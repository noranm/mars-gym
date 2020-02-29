import abc
import gc
import logging
import multiprocessing
import os
import random
import shutil
from contextlib import redirect_stdout
from typing import Type, Dict, List, Optional
import json
import luigi
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.nn.init import xavier_normal
from torch.optim import Adam, RMSprop, SGD
from torch.optim.adadelta import Adadelta
from torch.optim.adagrad import Adagrad
from torch.optim.adamax import Adamax
from torch.optim.optimizer import Optimizer
from torch.utils.data import DataLoader
from torch.utils.data._utils.collate import default_convert
from torch.utils.data.dataset import Dataset
import torchbearer
from torchbearer import Trial
from torchbearer.callbacks import GradientNormClipping
from torchbearer.callbacks.checkpointers import ModelCheckpoint
from torchbearer.callbacks.csv_logger import CSVLogger
from torchbearer.callbacks.early_stopping import EarlyStopping
from torchbearer.callbacks.tensor_board import TensorBoard

from recommendation.files import get_params_path, get_weights_path, get_params, get_history_path, \
    get_tensorboard_logdir, get_task_dir
from recommendation.loss import ImplicitFeedbackBCELoss, CounterfactualRiskMinimization
from recommendation.plot import plot_history
from recommendation.summary import summary
from recommendation.task.config import PROJECTS, IOType
from recommendation.task.cuda import CudaRepository
from recommendation.torch import NoAutoCollationDataLoader, RAdam, FasterBatchSampler
from recommendation.utils import lecun_normal_init, he_init

logging.basicConfig(format='%(asctime)s : %(levelname)s : %(message)s', level=logging.INFO)

TORCH_OPTIMIZERS = dict(adam=Adam, rmsprop=RMSprop, sgd=SGD, adadelta=Adadelta, adagrad=Adagrad, adamax=Adamax,
                        radam=RAdam)
TORCH_LOSS_FUNCTIONS = dict(mse=nn.MSELoss, nll=nn.NLLLoss, bce=nn.BCELoss, mlm=nn.MultiLabelMarginLoss,
                            implicit_feedback_bce=ImplicitFeedbackBCELoss, crm=CounterfactualRiskMinimization)
TORCH_ACTIVATION_FUNCTIONS = dict(relu=F.relu, selu=F.selu, tanh=F.tanh, sigmoid=F.sigmoid, linear=F.linear)
TORCH_WEIGHT_INIT = dict(lecun_normal=lecun_normal_init, he=he_init, xavier_normal=xavier_normal)
TORCH_DROPOUT_MODULES = dict(dropout=nn.Dropout, alpha=nn.AlphaDropout)

SEED = 42

DEFAULT_DEVICE = "cuda" if torch.cuda.is_available() else "cpu"


class BaseModelTraining(luigi.Task):
    __metaclass__ = abc.ABCMeta

    project: str = luigi.ChoiceParameter(choices=PROJECTS.keys())

    sample_size: int = luigi.IntParameter(default=-1)
    minimum_interactions: int = luigi.FloatParameter(default=5)
    session_test_size: float = luigi.FloatParameter(default=0.10)
    test_size: float = luigi.FloatParameter(default=0.0)
    dataset_split_method: str = luigi.ChoiceParameter(choices=["holdout", "column", "time", "k_fold"], default="holdout")
    val_size: float = luigi.FloatParameter(default=0.2)
    n_splits: int = luigi.IntParameter(default=5)
    split_index: int = luigi.IntParameter(default=0)
    data_frames_preparation_extra_params: dict = luigi.DictParameter(default={})
    sampling_strategy: str = luigi.ChoiceParameter(choices=["oversample", "undersample", "none"], default="none")
    balance_fields: List[str] = luigi.ListParameter(default=[])
    sampling_proportions: Dict[str, Dict[str, float]] = luigi.DictParameter(default={})
    use_sampling_in_validation: bool = luigi.BoolParameter(default=False)
    eq_filters: Dict[str, any] = luigi.DictParameter(default={})
    neq_filters: Dict[str, any] = luigi.DictParameter(default={})
    isin_filters: Dict[str, any] = luigi.DictParameter(default={})
    seed: int = luigi.IntParameter(default=SEED)

    @property
    def cache_attrs(self):
        return ['_test_dataset', '_val_dataset', '_train_dataset',
                '_test_data_frame', '_val_data_frame', '_train_data_frame', '_metadata_data_frame']

    def requires(self):
        return self.project_config.prepare_data_frames_task(session_test_size=self.session_test_size,
                                                            sample_size=self.sample_size,
                                                            minimum_interactions=self.minimum_interactions,
                                                            test_size=self.test_size,
                                                            dataset_split_method=self.dataset_split_method,
                                                            val_size=self.val_size,
                                                            n_splits=self.n_splits,
                                                            split_index=self.split_index,
                                                            sampling_strategy=self.sampling_strategy,
                                                            sampling_proportions=self.sampling_proportions,
                                                            balance_fields=self.balance_fields or self.project_config.default_balance_fields,
                                                            use_sampling_in_validation=self.use_sampling_in_validation,
                                                            eq_filters=self.eq_filters,
                                                            neq_filters=self.neq_filters,
                                                            isin_filters=self.isin_filters,
                                                            seed=self.seed,
                                                            **self.data_frames_preparation_extra_params)

    def output(self):
        return luigi.LocalTarget(get_task_dir(self.__class__, self.task_id))

    @property
    def project_config(self):
        return PROJECTS[self.project]

    def _save_params(self):
        with open(get_params_path(self.output().path), "w") as params_file:
            json.dump(self.param_kwargs, params_file, default=lambda o: dict(o), indent=4)

    @property
    def train_data_frame_path(self) -> str:
        return self.input()[0].path

    @property
    def val_data_frame_path(self) -> str:
        return self.input()[1].path

    @property
    def test_data_frame_path(self) -> str:
        return self.input()[2].path

    @property
    def metadata_data_frame_path(self) -> Optional[str]:
        if len(self.input()) > 3:
            return self.input()[3].path
        else:
            return None

    @property
    def metadata_data_frame(self) -> Optional[pd.DataFrame]:
        if not hasattr(self, "_metadata_data_frame"):
            self._metadata_data_frame = pd.read_csv(self.metadata_data_frame_path) \
                if self.metadata_data_frame_path else None
        return self._metadata_data_frame

    @property
    def train_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_train_data_frame"):
            self._train_data_frame = pd.read_csv(self.train_data_frame_path)
        return self._train_data_frame

    @property
    def val_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_val_data_frame"):
            self._val_data_frame = pd.read_csv(self.val_data_frame_path)
        return self._val_data_frame

    @property
    def test_data_frame(self) -> pd.DataFrame:
        if not hasattr(self, "_test_data_frame"):
            self._test_data_frame = pd.read_csv(self.test_data_frame_path)
        return self._test_data_frame

    @property
    def train_dataset(self) -> Dataset:
        if not hasattr(self, "_train_dataset"):
            self._train_dataset = self.project_config.dataset_class(
                self.train_data_frame, self.metadata_data_frame, self.project_config)
        return self._train_dataset

    @property
    def val_dataset(self) -> Dataset:
        if not hasattr(self, "_val_dataset"):
            self._val_dataset = self.project_config.dataset_class(
                self.val_data_frame, self.metadata_data_frame, self.project_config)
        return self._val_dataset

    @property
    def test_dataset(self) -> Dataset:
        if not hasattr(self, "_test_dataset"):
            self._test_dataset = self.project_config.dataset_class(
                self.test_data_frame, self.metadata_data_frame, self.project_config)
        return self._test_dataset

    @property
    def vocab_size(self):
        if not hasattr(self, "_vocab_size"):
            self._vocab_size = int(self.train_data_frame.iloc[0]["vocab_size"])
        return self._vocab_size

    @property
    def n_users(self) -> int:
        if not hasattr(self, "_n_users"):
            self._n_users = int(self.train_data_frame.iloc[0][self.project_config.n_users_column])
        return self._n_users

    @property
    def n_items(self) -> int:
        if not hasattr(self, "_n_items"):
            self._n_items = int(self.train_data_frame.iloc[0][self.project_config.n_items_column])
        return self._n_items

    @abc.abstractmethod
    def train(self):
        pass

    def cache_cleanup(self):
        for a in self.cache_attrs:
            if hasattr(self, a):
                delattr(self, a)

    def seed_everything(self):
        random.seed(self.seed)
        os.environ['PYTHONHASHSEED'] = str(self.seed)
        np.random.seed(self.seed)
        torch.manual_seed(self.seed)
        torch.cuda.manual_seed(self.seed)
        torch.backends.cudnn.deterministic = True
        torch.backends.cudnn.benchmark = False

    def run(self):
        self.seed_everything()

        os.makedirs(self.output().path, exist_ok=True)
        self._save_params()
        try:
            self.train()
        except Exception:
            shutil.rmtree(self.output().path)
            raise
        finally:
            gc.collect()
            if self.device == "cuda":
                CudaRepository.put_available_device(self.device_id)


class BaseTorchModelTraining(BaseModelTraining):
    __metaclass__ = abc.ABCMeta

    device: str = luigi.ChoiceParameter(choices=["cpu", "cuda"], default=DEFAULT_DEVICE)

    batch_size: int = luigi.IntParameter(default=500)
    epochs: int = luigi.IntParameter(default=100)
    optimizer: str = luigi.ChoiceParameter(choices=TORCH_OPTIMIZERS.keys(), default="adam")
    optimizer_params: dict = luigi.DictParameter(default={})
    learning_rate: float = luigi.FloatParameter(1e-3)
    loss_function: str = luigi.ChoiceParameter(choices=TORCH_LOSS_FUNCTIONS.keys(), default="mse")
    loss_function_params: dict = luigi.DictParameter(default={})
    gradient_norm_clipping: float = luigi.FloatParameter(default=0.0)
    gradient_norm_clipping_type: float = luigi.IntParameter(default=2)
    early_stopping_patience: int = luigi.IntParameter(default=5)
    early_stopping_min_delta: float = luigi.FloatParameter(default=1e-3)
    monitor_metric: str = luigi.Parameter(default="val_loss")
    monitor_mode: str = luigi.Parameter(default="min")
    generator_workers: int = luigi.IntParameter(default=0)
    pin_memory: bool = luigi.BoolParameter(default=False)

    metrics = luigi.ListParameter(default=["loss"])

    @property
    def resources(self):
        return {"cuda": 1} if self.device == "cuda" else {}

    @property
    def device_id(self):
        if not hasattr(self, "_device_id"):
            if self.device == "cuda":
                self._device_id = CudaRepository.get_avaliable_device()
            else:
                self._device_id = None
        return self._device_id

    @abc.abstractmethod
    def create_module(self) -> nn.Module:
        pass

    def train(self):
        if self.device == "cuda":
            torch.cuda.set_device(self.device_id)

        train_loader    = self.get_train_generator()
        val_loader      = self.get_val_generator()
        module          = self.create_module()

        summary_path = os.path.join(self.output().path, "summary.txt")
        with open(summary_path, "w") as summary_file:
            with redirect_stdout(summary_file):
                sample_input = default_convert(self.train_dataset[0][0])
                summary(module, sample_input)
            summary(module, sample_input)

        trial = self.create_trial(module)

        try:
            trial.with_generators(train_generator=train_loader, val_generator=val_loader).run(epochs=self.epochs)
        except KeyboardInterrupt:
            print("Finishing the training at the request of the user...")

        history_df = pd.read_csv(get_history_path(self.output().path))

        plot_history(history_df).savefig(os.path.join(self.output().path, "history.jpg"))

        self.after_fit()
        self.evaluate()
        self.cache_cleanup()


    def after_fit(self):
        pass

    def evaluate(self):
        module      = self.get_trained_module()
        val_loader  = self.get_val_generator()

        print("================== Evaluate ========================")
        trial = Trial(module, self._get_optimizer(module), self._get_loss_function(), callbacks=[],
                      metrics=self.metrics).to(self.torch_device)\
                    .with_generators(val_generator=val_loader).eval()

        print(json.dumps((trial.evaluate(data_key=torchbearer.VALIDATION_DATA)), indent = 4))
        

    def create_trial(self, module: nn.Module) -> Trial:
        loss_function = self._get_loss_function()
        trial = Trial(module, self._get_optimizer(module), loss_function, callbacks=self._get_callbacks(),
                      metrics=self.metrics).to(self.torch_device)
        if hasattr(loss_function, "torchbearer_state"):
            loss_function.torchbearer_state = trial.state
        return trial

    def _get_loss_function(self):
        return TORCH_LOSS_FUNCTIONS[self.loss_function](**self.loss_function_params)

    def _get_optimizer(self, module) -> Optimizer:
        return TORCH_OPTIMIZERS[self.optimizer](module.parameters(), lr=self.learning_rate,
                                                **self.optimizer_params)

    def _get_callbacks(self):
        callbacks = [
            *self._get_extra_callbacks(),
            ModelCheckpoint(get_weights_path(self.output().path), save_best_only=True, monitor=self.monitor_metric,
                            mode=self.monitor_mode),
            EarlyStopping(patience=self.early_stopping_patience, min_delta=self.early_stopping_min_delta,
                          monitor=self.monitor_metric, mode=self.monitor_mode),
            CSVLogger(get_history_path(self.output().path)),
            TensorBoard(get_tensorboard_logdir(self.task_id), write_graph=False),
        ]
        if self.gradient_norm_clipping:
            callbacks.append(GradientNormClipping(self.gradient_norm_clipping, self.gradient_norm_clipping_type))
        return callbacks

    def _get_extra_callbacks(self):
        return []

    def get_trained_module(self) -> nn.Module:
        module = self.create_module().to(self.torch_device)
        state_dict = torch.load(get_weights_path(self.output().path), map_location=self.torch_device)
        module.load_state_dict(state_dict["model"])
        module.eval()
        return module

    @property
    def torch_device(self) -> torch.device:
        if not hasattr(self, "_torch_device"):
            if self.device == "cuda":
                self._torch_device = torch.device(f"cuda:{self.device_id}")
            else:
                self._torch_device = torch.device("cpu")
        return self._torch_device

    def get_train_generator(self) -> DataLoader:
        batch_sampler = FasterBatchSampler(self.train_dataset, self.batch_size, shuffle=True)
        return NoAutoCollationDataLoader(self.train_dataset, batch_sampler=batch_sampler,
                                         num_workers=self.generator_workers,
                                         pin_memory=self.pin_memory if self.device == "cuda" else False)

    def get_val_generator(self) -> DataLoader:
        batch_sampler = FasterBatchSampler(self.val_dataset, self.batch_size, shuffle=False)
        return NoAutoCollationDataLoader(self.val_dataset, batch_sampler=batch_sampler,
                                         num_workers=self.generator_workers,
                                         pin_memory=self.pin_memory if self.device == "cuda" else False)

    def get_test_generator(self) -> DataLoader:
        batch_sampler = FasterBatchSampler(self.test_dataset, self.batch_size, shuffle=False)
        return NoAutoCollationDataLoader(self.test_dataset, batch_sampler=batch_sampler,
                                         num_workers=self.generator_workers,
                                         pin_memory=True if self.device == "cuda" else False)


def load_torch_model_training_from_task_dir(model_cls: Type[BaseTorchModelTraining],
                                            task_dir: str) -> BaseTorchModelTraining:
    return model_cls(**get_params(task_dir))


def load_torch_model_training_from_task_id(model_cls: Type[BaseTorchModelTraining],
                                           task_id: str) -> BaseTorchModelTraining:
    task_dir = get_task_dir(model_cls, task_id)

    return load_torch_model_training_from_task_dir(model_cls, task_dir)

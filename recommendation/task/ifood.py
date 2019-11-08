import functools
import functools
import json
import math
import os
from itertools import starmap
from multiprocessing.pool import Pool
from typing import Dict, Tuple, List

import luigi
import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from recommendation.data import literal_eval_array_columns
from recommendation.plot import plot_histogram
from recommendation.rank_metrics import average_precision, ndcg_at_k, prediction_coverage_at_k, personalization_at_k
from recommendation.task.data_preparation.ifood import PrepareIfoodIndexedOrdersTestData, \
    ListAccountMerchantTuplesForIfoodIndexedOrdersTestData, ProcessRestaurantContentDataset, \
    PrepareRestaurantContentDataset, \
    CreateInteractionDataset, GenerateIndicesForAccountsAndMerchantsOfSessionTrainDataset
from recommendation.task.evaluation import BaseEvaluationTask
from recommendation.utils import chunks, parallel_literal_eval


def _sort_merchants_by_tuple_score(account_idx: int, merchant_idx_list: List[int],
                                   scores_per_tuple: Dict[Tuple[int, int], float]) -> List[int]:
    scores = list(map(lambda merchant_idx: scores_per_tuple.get((account_idx, merchant_idx), -1.0), merchant_idx_list))
    return [merchant_idx for _, merchant_idx in sorted(zip(scores, merchant_idx_list), reverse=True)]


def _sort_merchants_by_merchant_score(merchant_idx_list: List[int], scores_per_merchant: Dict[int, float]) -> List[int]:
    scores = list(map(lambda merchant_idx: scores_per_merchant[merchant_idx], merchant_idx_list))
    return [merchant_idx for _, merchant_idx in
                                sorted(zip(scores, merchant_idx_list), reverse=True)]


def _create_relevance_list(sorted_merchant_idx_list: List[int], ordered_merchant_idx: int) -> List[int]:
    return [1 if merchant_idx == ordered_merchant_idx else 0 for merchant_idx in sorted_merchant_idx_list]


def _generate_relevance_list(account_idx: int, ordered_merchant_idx: int, merchant_idx_list: List[int],
                             scores_per_tuple: Dict[Tuple[int, int], float]) -> List[int]:
    scores = list(map(lambda merchant_idx: scores_per_tuple.get((account_idx, merchant_idx), -1.0), merchant_idx_list))
    sorted_merchant_idx_list = [merchant_idx for _, merchant_idx in
                                sorted(zip(scores, merchant_idx_list), reverse=True)]
    return [1 if merchant_idx == ordered_merchant_idx else 0 for merchant_idx in sorted_merchant_idx_list]


def _generate_random_relevance_list(ordered_merchant_idx: int, merchant_idx_list: List[int]) -> List[int]:
    np.random.shuffle(merchant_idx_list)
    return _create_relevance_list(merchant_idx_list, ordered_merchant_idx)


def _generate_relevance_list_from_merchant_scores(ordered_merchant_idx: int, merchant_idx_list: List[int],
                                                  scores_per_merchant: Dict[int, float]) -> List[int]:
    scores = list(map(lambda merchant_idx: scores_per_merchant[merchant_idx], merchant_idx_list))
    sorted_merchant_idx_list = [merchant_idx for _, merchant_idx in
                                sorted(zip(scores, merchant_idx_list), reverse=True)]
    return [1 if merchant_idx == ordered_merchant_idx else 0 for merchant_idx in sorted_merchant_idx_list]


class SortMerchantListsForIfoodModel(BaseEvaluationTask):
    batch_size: int = luigi.IntParameter(default=100000)

    # num_processes: int = luigi.IntParameter(default=os.cpu_count())

    def requires(self):
        test_size = self.model_training.requires().session_test_size
        return PrepareIfoodIndexedOrdersTestData(test_size=test_size), \
               ListAccountMerchantTuplesForIfoodIndexedOrdersTestData(test_size=test_size)

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.model_task_id, "orders_with_relevance_lists.csv"))

    def _generate_batch_tensors(self, rows: pd.DataFrame, pool: Pool) -> List[torch.Tensor]:
        return [torch.tensor(rows[input_column.name].values, dtype=torch.int64)
                    .to(self.model_training.torch_device)
                for input_column in self.model_training.project_config.input_columns]

    def _evaluate_account_merchant_tuples(self) -> Dict[Tuple[int, int], float]:
        print("Reading tuples files...")
        tuples_df = pd.read_parquet(self.input()[1].path)

        assert self.model_training.project_config.input_columns[0].name == "account_idx"
        assert self.model_training.project_config.input_columns[1].name == "merchant_idx"

        print("Loading trained model...")
        module = self.model_training.get_trained_module()
        scores: List[float] = []
        print("Running the model for every account and merchant tuple...")
        with Pool(os.cpu_count()) as pool:
            for indices in tqdm(chunks(range(len(tuples_df)), self.batch_size),
                                total=math.ceil(len(tuples_df) / self.batch_size)):
                rows: pd.DataFrame = tuples_df.iloc[indices]
                inputs = self._generate_batch_tensors(rows, pool)
                batch_scores: torch.Tensor = module(*inputs)
                scores.extend(batch_scores.detach().cpu().numpy())

        print("Creating the dictionary of scores...")
        return {(account_idx, merchant_idx): score for account_idx, merchant_idx, score
                in tqdm(zip(tuples_df["account_idx"], tuples_df["merchant_idx"], scores), total=len(scores))}

    def run(self):
        os.makedirs(os.path.split(self.output().path)[0], exist_ok=True)

        scores_per_tuple = self._evaluate_account_merchant_tuples()

        print("Reading the orders DataFrame...")
        orders_df: pd.DataFrame = pd.read_parquet(self.input()[0].path)

        print("Filtering orders where the ordered merchant isn't in the list...")
        orders_df = orders_df[orders_df.apply(lambda row: row["merchant_idx"] in row["merchant_idx_list"], axis=1)]

        print("Sorting the merchant lists")
        orders_df["sorted_merchant_idx_list"] = list(tqdm(
            starmap(functools.partial(_sort_merchants_by_tuple_score, scores_per_tuple=scores_per_tuple),
                    zip(orders_df["account_idx"], orders_df["merchant_idx_list"])),
            total=len(orders_df)))

        print("Creating the relevance lists...")
        orders_df["relevance_list"] = list(tqdm(
            starmap(_create_relevance_list, zip(orders_df["sorted_merchant_idx_list"], orders_df["merchant_idx"])),
            total=len(orders_df)))

        # with mp.Manager() as manager:
        #     shared_scores_per_tuple: Dict[Tuple[int, int], float] = manager.dict(scores_per_tuple)
        #     with manager.Pool(self.num_processes) as p:
        #         orders_df["relevance_list"] = list(tqdm(
        #             starmap(functools.partial(_generate_relevance_list, scores_per_tuple=shared_scores_per_tuple),
        #                     zip(orders_df["account_idx"], orders_df["merchant_idx"], orders_df["merchant_idx_list"])),
        #             total=len(orders_df)))

        print("Saving the output file...")

        plot_histogram(scores_per_tuple.values()).savefig(
            os.path.join(os.path.split(self.output().path)[0], "scores_histogram.jpg"))
        orders_df[["session_id", "relevance_list"]].to_csv(self.output().path, index=False)


class SortMerchantListsForAutoEncoderIfoodModel(SortMerchantListsForIfoodModel):
    variational = luigi.BoolParameter(default=False)
    attentive = luigi.BoolParameter(default=False)
    context = luigi.BoolParameter(default=False)

    batch_size: int = luigi.IntParameter(default=500)

    def _eval_buys_per_merchant_column(self, df: pd.DataFrame):
        if len(df) > 0 and type(df.iloc[0]["buys_per_merchant"]) is str:
            df["buys_per_merchant"] = parallel_literal_eval(df["buys_per_merchant"])
        return df

    def _evaluate_account_merchant_tuples(self) -> Dict[Tuple[int, int], float]:
        assert self.model_training.project_config.input_columns[0].name == "buys_per_merchant"
        assert self.model_training.project_config.output_column.name == "buys_per_merchant"

        print("Reading tuples files...")
        tuples_df = pd.read_parquet(self.input()[1].path)

        print("Grouping by account index...")
        merchant_indices_per_account_idx: pd.Series = tuples_df.groupby('account_idx')['merchant_idx'].apply(list)
        del tuples_df

        print("Reading train, val and test DataFrames...")
        train_df = self._eval_buys_per_merchant_column(pd.read_csv(self.model_training.input()[0].path))
        val_df = self._eval_buys_per_merchant_column(pd.read_csv(self.model_training.input()[1].path))
        test_df = self._eval_buys_per_merchant_column(pd.read_csv(self.model_training.input()[2].path))
        df: pd.DataFrame = pd.concat((train_df, val_df, test_df))

        # Needed if split_per_user=False
        df = df.groupby("account_idx")["buys_per_merchant"] \
            .apply(lambda lists: [inner for outer in lists for inner in outer]).reset_index()

        print("Loading trained model...")
        module = self.model_training.get_trained_module()

        scores_per_tuple: List[Tuple[Tuple[int, int], float]] = []

        print("Running the model for every account and merchant tuple...")
        for indices in tqdm(chunks(range(len(df)), self.batch_size),
                            total=math.ceil(len(df) / self.batch_size)):
            rows: pd.DataFrame = df.iloc[indices]

            i, j, data = zip(
                *((index, int(t[0]), t[1]) for index, row in enumerate(rows["buys_per_merchant"])
                  for t in row))
            batch_tensor = torch.sparse_coo_tensor(
                indices=torch.tensor([i, j]),
                values=torch.tensor(data),
                size=[len(rows), self.model_training.n_items]).to(self.model_training.torch_device)

            batch_output_tensor = None
            if self.context:
                batch_context = torch.tensor(rows['account_idx'].values).to(self.model_training.torch_device)
                batch_output_tensor = module(batch_tensor, batch_context)
            else:
                batch_output_tensor = module(batch_tensor)

            if self.attentive:
                batch_output_tensor, _, _, _, _ = batch_output_tensor
            elif self.variational:
                batch_output_tensor, _, _ = batch_output_tensor

            batch_output: np.ndarray = batch_output_tensor.detach().cpu().numpy()

            for account_idx, row in zip(rows["account_idx"], batch_output):
                if account_idx in merchant_indices_per_account_idx:
                    merchant_indices = merchant_indices_per_account_idx[account_idx]
                    scores_per_tuple.extend([((account_idx, merchant_idx), row[merchant_idx])
                                             for merchant_idx in merchant_indices])

        print("Creating the dictionary of scores...")
        return dict(scores_per_tuple)


class SortMerchantListsTripletWeightedModel(SortMerchantListsForIfoodModel):

    def _generate_batch_tensors(self, rows: pd.DataFrame, pool: Pool) -> List[torch.Tensor]:
        assert self.model_training.project_config.input_columns[0].name == 'account_idx'
        assert self.model_training.project_config.input_columns[1].name == 'merchant_idx'

        return [torch.tensor(rows[column].values, dtype=torch.int64)
                    .to(self.model_training.torch_device)
                for column in ['account_idx', 'merchant_idx']]


class EvaluateIfoodModel(BaseEvaluationTask):
    num_processes: int = luigi.IntParameter(default=os.cpu_count())

    def requires(self):
        return SortMerchantListsForIfoodModel(model_module=self.model_module, model_cls=self.model_cls,
                                              model_task_id=self.model_task_id)

    def output(self):
        model_path = os.path.join("output", "evaluation", self.__class__.__name__, "results",
                                  self.model_task_id)
        return luigi.LocalTarget(os.path.join(model_path, "orders_with_metrics.csv")), \
               luigi.LocalTarget(os.path.join(model_path, "metrics.json")),

    def run(self):
        os.makedirs(os.path.split(self.output()[0].path)[0], exist_ok=True)

        df: pd.DataFrame = pd.read_csv(self.input().path)

        with Pool(self.num_processes) as p:
            df["sorted_merchant_idx_list"] = parallel_literal_eval(df["sorted_merchant_idx_list"], pool=p)
            df["relevance_list"] = parallel_literal_eval(df["relevance_list"], pool=p)

            df["average_precision"] = list(
                tqdm(p.map(average_precision, df["relevance_list"]), total=len(df)))

            df["ndcg_at_5"] = list(
                tqdm(p.map(functools.partial(ndcg_at_k, k=5), df["relevance_list"]), total=len(df)))
            df["ndcg_at_10"] = list(
                tqdm(p.map(functools.partial(ndcg_at_k, k=10), df["relevance_list"]), total=len(df)))
            df["ndcg_at_15"] = list(
                tqdm(p.map(functools.partial(ndcg_at_k, k=15), df["relevance_list"]), total=len(df)))
            df["ndcg_at_20"] = list(
                tqdm(p.map(functools.partial(ndcg_at_k, k=20), df["relevance_list"]), total=len(df)))
            df["ndcg_at_50"] = list(
                tqdm(p.map(functools.partial(ndcg_at_k, k=50), df["relevance_list"]), total=len(df)))

        catalog = range(self.model_training.n_items)

        metrics = {
            "count": len(df),
            "mean_average_precision": df["average_precision"].mean(),
            "ndcg_at_5": df["ndcg_at_5"].mean(),
            "ndcg_at_10": df["ndcg_at_10"].mean(),
            "ndcg_at_15": df["ndcg_at_15"].mean(),
            "ndcg_at_20": df["ndcg_at_20"].mean(),
            "ndcg_at_50": df["ndcg_at_50"].mean(),
            "coverage_at_5": prediction_coverage_at_k(df["sorted_merchant_idx_list"], catalog, 5),
            "coverage_at_10": prediction_coverage_at_k(df["sorted_merchant_idx_list"], catalog, 10),
            "coverage_at_15": prediction_coverage_at_k(df["sorted_merchant_idx_list"], catalog, 15),
            "coverage_at_20": prediction_coverage_at_k(df["sorted_merchant_idx_list"], catalog, 20),
            "coverage_at_50": prediction_coverage_at_k(df["sorted_merchant_idx_list"], catalog, 50),
            "personalization_at_5": personalization_at_k(df["sorted_merchant_idx_list"], 5),
            "personalization_at_10": personalization_at_k(df["sorted_merchant_idx_list"], 10),
            "personalization_at_15": personalization_at_k(df["sorted_merchant_idx_list"], 15),
            "personalization_at_20": personalization_at_k(df["sorted_merchant_idx_list"], 20),
            "personalization_at_50": personalization_at_k(df["sorted_merchant_idx_list"], 20),
        }

        df = df.drop(columns=["sorted_merchant_idx_list", "relevance_list"])
        df.to_csv(self.output()[0].path)
        with open(self.output()[1].path, "w") as metrics_file:
            json.dump(metrics, metrics_file, indent=4)


class SortMerchantListsRandomly(luigi.Task):
    test_size: float = luigi.FloatParameter(default=0.2)

    def requires(self):
        return PrepareIfoodIndexedOrdersTestData(test_size=self.test_size)

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.task_id, "orders_with_relevance_lists.csv"))

    def run(self):
        os.makedirs(os.path.split(self.output().path)[0], exist_ok=True)

        print("Reading the orders DataFrame...")
        orders_df: pd.DataFrame = pd.read_parquet(self.input().path)

        print("Filtering orders where the ordered merchant isn't in the list...")
        orders_df = orders_df[orders_df.apply(lambda row: row["merchant_idx"] in row["merchant_idx_list"], axis=1)]

        print("Sorting the merchant lists")
        orders_df["sorted_merchant_idx_list"] = list(tqdm(
            map(np.random.shuffle, orders_df["merchant_idx_list"]),
            total=len(orders_df)))

        print("Creating the relevance lists...")
        orders_df["relevance_list"] = list(tqdm(
            starmap(_create_relevance_list, zip(orders_df["sorted_merchant_idx_list"], orders_df["merchant_idx"])),
            total=len(orders_df)))

        print("Saving the output file...")
        orders_df[["session_id", "relevance_list"]].to_csv(self.output().path, index=False)


class EvaluateIfoodCDAEModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsForAutoEncoderIfoodModel(model_module=self.model_module, model_cls=self.model_cls,
                                                         model_task_id=self.model_task_id)


class EvaluateIfoodCVAEModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsForAutoEncoderIfoodModel(model_module=self.model_module, model_cls=self.model_cls,
                                                         model_task_id=self.model_task_id,
                                                         variational=True)


class EvaluateIfoodAttCVAEModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsForAutoEncoderIfoodModel(model_module=self.model_module, model_cls=self.model_cls,
                                                         model_task_id=self.model_task_id,
                                                         attentive=True)


class EvaluateIfoodHybridCVAEModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsForAutoEncoderIfoodModel(model_module=self.model_module, model_cls=self.model_cls,
                                                         model_task_id=self.model_task_id, context=True,
                                                         variational=True)


class EvaluateRandomIfoodModel(EvaluateIfoodModel):
    model_task_id: str = luigi.Parameter(default="none")

    def requires(self):
        return SortMerchantListsRandomly()


class SortMerchantListsByMostPopular(luigi.Task):
    model_task_id: str = luigi.Parameter(default="none")
    test_size: float = luigi.FloatParameter(default=0.2)

    def requires(self):
        return CreateInteractionDataset(test_size=self.test_size), \
               PrepareIfoodIndexedOrdersTestData(test_size=self.test_size)

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.task_id, "orders_with_relevance_lists.csv"))

    def run(self):
        os.makedirs(os.path.split(self.output().path)[0], exist_ok=True)

        print("Reading the interactions DataFrame...")
        interactions_df: pd.DataFrame = pd.read_parquet(self.input()[0].path)
        print("Generating the scores")
        scores: pd.Series = interactions_df.groupby("merchant_idx")["buys"].sum()
        scores_dict: Dict[int, float] = {merchant_idx: score for merchant_idx, score
                                         in tqdm(zip(scores.index, scores),
                                                 total=len(scores))}

        print("Reading the orders DataFrame...")
        orders_df: pd.DataFrame = pd.read_parquet(self.input()[1].path)

        print("Filtering orders where the ordered merchant isn't in the list...")
        orders_df = orders_df[orders_df.apply(lambda row: row["merchant_idx"] in row["merchant_idx_list"], axis=1)]

        print("Sorting the merchant lists")
        orders_df["sorted_merchant_idx_list"] = list(tqdm(
            starmap(functools.partial(_sort_merchants_by_merchant_score, scores_per_merchant=scores_dict),
                    zip(orders_df["merchant_idx_list"])),
            total=len(orders_df)))

        print("Creating the relevance lists...")
        orders_df["relevance_list"] = list(tqdm(
            starmap(_create_relevance_list, zip(orders_df["sorted_merchant_idx_list"], orders_df["merchant_idx"])),
            total=len(orders_df)))

        print("Saving the output file...")
        orders_df[["session_id", "relevance_list"]].to_csv(self.output().path, index=False)


class EvaluateMostPopularIfoodModel(EvaluateIfoodModel):
    model_task_id: str = luigi.Parameter(default="none")

    def requires(self):
        return SortMerchantListsByMostPopular()


class SortMerchantListsByMostPopularPerUser(luigi.Task):
    model_task_id: str = luigi.Parameter(default="none")
    test_size: float = luigi.FloatParameter(default=0.2)
    buy_importance: float = luigi.FloatParameter(default=1.0)
    visit_importance: float = luigi.FloatParameter(default=0.0)

    def requires(self):
        return CreateInteractionDataset(test_size=self.test_size), \
               PrepareIfoodIndexedOrdersTestData(test_size=self.test_size)

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.task_id + "GenerateMostPopularPerUserRelevanceLists_buy_importance=%.2f_visit_importance=%.2f" % (
                             self.buy_importance,
                             self.visit_importance),
                         "orders_with_relevance_lists.csv"))

    def run(self):
        os.makedirs(os.path.split(self.output().path)[0], exist_ok=True)

        print("Reading the interactions DataFrame...")
        interactions_df: pd.DataFrame = pd.read_parquet(self.input()[0].path)
        print("Generating the scores")
        grouped_interactions = interactions_df.groupby(["account_idx", "merchant_idx"])
        scores: pd.Series = grouped_interactions["buys"].sum() * self.buy_importance \
                            + grouped_interactions["visits"].sum() * self.visit_importance
        scores_per_tuple: Dict[Tuple[int, int], float] = {(account_idx, merchant_idx): score
                                                          for (account_idx, merchant_idx), score
                                                          in tqdm(zip(scores.index, scores), total=len(scores))}

        print("Reading the orders DataFrame...")
        orders_df: pd.DataFrame = pd.read_parquet(self.input()[1].path)

        print("Filtering orders where the ordered merchant isn't in the list...")
        orders_df = orders_df[orders_df.apply(lambda row: row["merchant_idx"] in row["merchant_idx_list"], axis=1)]

        print("Sorting the merchant lists")
        orders_df["sorted_merchant_idx_list"] = list(tqdm(
            starmap(functools.partial(_sort_merchants_by_tuple_score, scores_per_tuple=scores_per_tuple),
                    zip(orders_df["account_idx"], orders_df["merchant_idx_list"])),
            total=len(orders_df)))

        print("Creating the relevance lists...")
        orders_df["relevance_list"] = list(tqdm(
            starmap(_create_relevance_list, zip(orders_df["sorted_merchant_idx_list"], orders_df["merchant_idx"])),
            total=len(orders_df)))

        print("Saving the output file...")
        orders_df[["session_id", "relevance_list"]].to_csv(self.output().path, index=False)


class EvaluateMostPopularPerUserIfoodModel(EvaluateIfoodModel):
    model_task_id: str = luigi.Parameter(default="none")
    buy_importance: float = luigi.FloatParameter(default=1.0)
    visit_importance: float = luigi.FloatParameter(default=0.0)

    def requires(self):
        return SortMerchantListsByMostPopularPerUser(buy_importance=self.buy_importance,
                                                     visit_importance=self.visit_importance)

    def output(self):
        model_path = os.path.join("output", "evaluation", self.__class__.__name__, "results",
                                  self.task_id + "_buy_importance=%.6f_visit_importance=%.6f" % (
                                      self.buy_importance,
                                      self.visit_importance))
        return luigi.LocalTarget(os.path.join(model_path, "orders_with_metrics.csv")), \
               luigi.LocalTarget(os.path.join(model_path, "metrics.json")),


class SortMerchantListsTripletContentModel(SortMerchantListsForIfoodModel):
    batch_size: int = luigi.IntParameter(default=10000)

    def requires(self):
        test_size = self.model_training.requires().session_test_size
        return super().requires() + (GenerateIndicesForAccountsAndMerchantsOfSessionTrainDataset(test_size=test_size),)

    def _evaluate_account_merchant_tuples(self) -> Dict[Tuple[int, int], float]:
        print("Reading merchant data frame...")
        self.merchant_df = pd.read_csv(self.input()[-1][1].path)

        literal_eval_array_columns(self.merchant_df,
                                   self.model_training.project_config.input_columns
                                   + [self.model_training.project_config.output_column]
                                   + self.model_training.project_config.metadata_columns)

        self.merchant_df = self.merchant_df.set_index("merchant_idx")

        return super()._evaluate_account_merchant_tuples()

    def _generate_content_tensors(self, rows):
        inputs = []

        for input_column in self.model_training.project_config.metadata_columns:
            dtype = torch.float32 if input_column.name == "restaurant_complete_info" else torch.int64
            values = rows[input_column.name].values.tolist()
            inputs.append(torch.tensor(values, dtype=dtype).to(self.model_training.torch_device))

        return inputs

    def _generate_batch_tensors(self, rows: pd.DataFrame, pool: Pool) -> List[torch.Tensor]:
        metadata_columns_name = [input_column.name for input_column in
                                 self.model_training.project_config.metadata_columns]

        assert metadata_columns_name == ['trading_name', 'description', 'category_names', 'restaurant_complete_info']

        account_idxs = torch.tensor(rows["account_idx"].values, dtype=torch.int64) \
            .to(self.model_training.torch_device)

        merchant_rows = self.merchant_df.loc[rows["merchant_idx"]]

        inputs = self._generate_content_tensors(merchant_rows)

        return [account_idxs, inputs]


class EvaluateIfoodTripletNetContentModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsTripletContentModel(model_module=self.model_module, model_cls=self.model_cls,
                                                    model_task_id=self.model_task_id)


class EvaluateIfoodTripletNetWeightedModel(EvaluateIfoodModel):
    def requires(self):
        return SortMerchantListsTripletWeightedModel(model_module=self.model_module, model_cls=self.model_cls,
                                                     model_task_id=self.model_task_id)


class GenerateContentEmbeddings(BaseEvaluationTask):
    batch_size: int = luigi.IntParameter(default=100000)

    def requires(self):
        return ProcessRestaurantContentDataset(), PrepareRestaurantContentDataset()

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.model_task_id, "restaurant_embeddings.tsv")), \
               luigi.LocalTarget(
                   os.path.join("output", "evaluation", self.__class__.__name__, "results",
                                self.model_task_id, "restaurant_metadata.tsv"))

    def _generate_content_tensors(self, rows):
        return SortMerchantListsTripletContentModel._generate_content_tensors(self, rows)

    def run(self):
        os.makedirs(os.path.split(self.output()[0].path)[0], exist_ok=True)

        processed_content_df = pd.read_csv(self.input()[0][0].path)

        literal_eval_array_columns(processed_content_df,
                                   self.model_training.project_config.input_columns
                                   + [self.model_training.project_config.output_column]
                                   + self.model_training.project_config.metadata_columns)

        print("Loading trained model...")
        module = self.model_training.get_trained_module()

        print("Generating embeddings for each merchant...")
        embeddings: List[float] = []
        for indices in tqdm(chunks(range(len(processed_content_df)), self.batch_size),
                            total=math.ceil(len(processed_content_df) / self.batch_size)):
            rows: pd.DataFrame = processed_content_df.iloc[indices]
            inputs = self._generate_content_tensors(rows)
            batch_embeddings: torch.Tensor = module.compute_item_embeddings(inputs)
            embeddings.extend(batch_embeddings.detach().cpu().numpy())

        restaurant_df = pd.read_csv(self.input()[1].path).replace(['\n', '\t'], ' ', regex=True)
        del restaurant_df['item_imagesurl']

        print("Saving the output file...")
        np.savetxt(os.path.join(self.output()[0].path), embeddings, delimiter="\t")
        restaurant_df.to_csv(os.path.join(self.output()[1].path), sep='\t', index=False)


class GenerateEmbeddings(BaseEvaluationTask):
    user_embeddings = luigi.BoolParameter(default=False)
    item_embeddings = luigi.BoolParameter(default=False)
    test_size: float = luigi.FloatParameter(default=0.2)

    def requires(self):
        return GenerateIndicesForAccountsAndMerchantsOfSessionTrainDataset(test_size=self.test_size)

    def output(self):
        return luigi.LocalTarget(
            os.path.join("output", "evaluation", self.__class__.__name__, "results",
                         self.model_task_id, "user_embeddings.tsv")), \
               luigi.LocalTarget(
                   os.path.join("output", "evaluation", self.__class__.__name__, "results",
                                self.model_task_id, "restaurant_embeddings.tsv")), \
               luigi.LocalTarget(
                   os.path.join("output", "evaluation", self.__class__.__name__, "results",
                                self.model_task_id, "restaurant_metadata.tsv"))

    def run(self):
        os.makedirs(os.path.split(self.output()[0].path)[0], exist_ok=True)

        print("Loading trained model...")
        module = self.model_training.get_trained_module()

        restaurant_df = pd.read_csv(self.input()[1].path)

        if self.user_embeddings:
            user_embeddings: np.ndarray = module.user_embeddings.weight.data.cpu().numpy()
            np.savetxt(self.output()[0].path, user_embeddings, delimiter="\t")

        if self.item_embeddings:
            item_embeddings: np.ndarray = module.item_embeddings.weight.data.cpu().numpy()
            np.savetxt(self.output()[1].path, item_embeddings, delimiter="\t")

        restaurant_df.to_csv(os.path.join(self.output()[2].path), sep='\t', index=False)

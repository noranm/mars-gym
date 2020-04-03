# Model
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy model

# Random
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy random


# Epsilon Greedy
docker run --gpus '"device=1"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy epsilon_greedy --bandit-policy-params '{"epsilon": 0.05}' 

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy epsilon_greedy --bandit-policy-params '{"epsilon": 0.1}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy epsilon_greedy --bandit-policy-params '{"epsilon": 0.2}'  

# lin_ucb
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ucb --bandit-policy-params '{"alpha": 1e-5}'   

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ucb --bandit-policy-params '{"alpha": 1e-2}'   

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ucb --bandit-policy-params '{"alpha": 1e-1}'   

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ucb --bandit-policy-params '{"alpha": 1}'   

# custom_lin_ucb
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy custom_lin_ucb --bandit-policy-params '{"alpha": 1e-5}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy custom_lin_ucb --bandit-policy-params '{"alpha": 1e-2}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy custom_lin_ucb --bandit-policy-params '{"alpha": 1e-1}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy custom_lin_ucb --bandit-policy-params '{"alpha": 1}'  

# # Lin TS
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ts --bandit-policy-params '{"v_sq": 0.1}' 

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ts --bandit-policy-params '{"v_sq": 0.5}' 

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy lin_ts --bandit-policy-params '{"v_sq": 1}' 


## softmax_explorer
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy softmax_explorer --bandit-policy-params '{"logit_multiplier": 0.1}' 

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy softmax_explorer --bandit-policy-params '{"logit_multiplier": 0.5}' 

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy softmax_explorer --bandit-policy-params '{"logit_multiplier": 1}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy softmax_explorer --bandit-policy-params '{"logit_multiplier": 5.0}'  

## Percentile_adaptive
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy percentile_adaptive --bandit-policy-params '{"exploration_threshold": 0.2}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy percentile_adaptive --bandit-policy-params '{"exploration_threshold": 0.5}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy percentile_adaptive --bandit-policy-params '{"exploration_threshold": 0.7}'  


## Adaptative
## 
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy adaptive --bandit-policy-params '{"exploration_threshold": 0.7, "decay_rate": 0.0000299366311063513}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy adaptive --bandit-policy-params '{"exploration_threshold": 0.5, "decay_rate": 0.0000268236054478970}'  

docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy adaptive --bandit-policy-params '{"exploration_threshold": 0.3, "decay_rate": 0.0000183100371803582}'  

## Explore the Exploit
# #https://www.wolframalpha.com/input/?i=0.1%3D0.8%281-r%29%5E2000
#
#
docker run --gpus '"device=0"' -i gcr.io/deepfood/deep-reco-gym:trivago-3.5 --module recommendation.task.model.trivago.trivago_logistic_model TrivagoLogisticModelInteraction --project trivago_contextual_bandit --data-frames-preparation-extra-params '{"filter_city": "Rio de Janeiro, Brazil", "window_hist": 10}' --n-factors 50 --learning-rate=0.001 --optimizer adam --metrics '["loss"]' --epochs 250 --obs-batch-size 1000 --val-split-type random --full-refit --early-stopping-patience 5 --batch-size 200 --num-episodes 7 --output-model-dir "gs://deepfood-results-rio_janeiro_brazil" --bandit-policy explore_then_exploit --bandit-policy-params '{"explore_rounds": 1500, "decay_rate": 0.0000416614429241702}'  
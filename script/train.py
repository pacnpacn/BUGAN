#!/usr/bin/env python
import os
import torch
import wandb
from argparse import Namespace
from pathlib import Path

from bugan.trainPL import (
    get_resume_run_config,
    get_bugan_package_revision_number,
    init_wandb_run,
    setup_datamodule,
    setup_model,
    train,
)


data_path = "../../handtool-data/handtool-v4-cleaned-tnf-1000.zip"
config_dict = {
    "data_location": data_path,
    "project_name": "handtool-gan",
    "resume_id": "7yd1hbta",
    "history_checkpoint_frequency": 2,
    "trim_class_offset": 0,
    "vae_opt": "Adam",
    "dis_opt": "Adam",
    "label_loss": "BCELoss",
    "rec_loss": "MSELoss",
    "accuracy_hack": 1.1,
    "vae_lr": 0.0001,
    "d_lr": 0.00001,
    "kl_coef": 300000,
    "d_rec_coef": 10000,
    "FMrec_coef": 0.01,
    "FMgan_coef": 0.1,
    "decoder_num_layer_unit": [256, 512, 256, 128, 128, 64],
    "encoder_num_layer_unit": [64, 128, 128, 256, 512, 256],
    "dis_num_layer_unit": [64, 128, 128, 256, 512, 256],
    "batch_size": 16,
    "resolution": 64,
    "log_interval": 20,
    "log_num_samples": 3,
    "label_flip_prob": 0,
    "label_noise": 0,
    "instance_noise_per_batch": True,
    "linear_annealed_instance_noise_epoch": 1000,
    "instance_noise": 0,
    "z_size": 512,
    "activation_leakyReLU_slope": 0.1,
    "dropout_prob": 0,
    "spectral_norm": False,
    "kernel_size": 5,
    "fc_size": 2,
    "use_simple_3dgan_struct": False,
}
config = Namespace(**config_dict)
dataset_path = Path(config.data_location)
if str(config.data_location).endswith(".zip"):
    config.dataset = dataset_path.stem
else:
    config.dataset = "dataset_array_custom"

# run offline
# os.environ["WANDB_MODE"] = "dryrun"

# get previous config if resume run
if config.resume_id:
    project_name = config.project_name
    resume_id = config.resume_id
    prev_config = get_resume_run_config(project_name, resume_id)
    # replace config with prev_config
    config = vars(config)
    config.update(vars(prev_config))
    config = Namespace(**config)
    config.resume_id = resume_id
    config.data_location = data_path

# write bugan package revision number to bugan
config.rev_number = get_bugan_package_revision_number()

run, config = init_wandb_run(config, run_dir="../../")  # , mode="offline")
run.notes = "testing train.py"

# specify another tmp folder for non colab

tmp_folder = str(Path(data_path).stem)
dataModule = setup_datamodule(config, tmp_folder)
model, extra_trainer_args = setup_model(config, run)

if torch.cuda.is_available():
    extra_trainer_args["gpus"] = -1
    extra_trainer_args["accelerator"] = "dp"
    print("cuda available! use all gpu in the machine")

train(config, run, model, dataModule, extra_trainer_args)
run.finish()

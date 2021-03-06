from argparse import Namespace

import os
import numpy as np
import pytest
import torch
import wandb
import pytorch_lightning as pl
from pathlib import Path

from bugan.modelsPL import (
    VAEGAN,
    VAE_train,
    GAN,
    GAN_Wloss,
    GAN_Wloss_GP,
    CGAN,
    CVAEGAN,
    ZVAEGAN,
)
from bugan.datamodulePL import DataModule_process
from bugan.trainPL import (
    get_resume_run_config,
    get_bugan_package_revision_number,
    init_wandb_run,
    setup_datamodule,
    setup_model,
    train,
    save_model_args,
    load_model_args,
    setup_config_arguments,
)
from test_data_loader import data_path


@pytest.mark.filterwarnings("ignore::DeprecationWarning")
@pytest.fixture
def device():
    # NOTE: some tests currently don't work with CUDA backend
    return torch.device("cpu")


@pytest.fixture
def wandb_run_dir(tmp_path):
    wandb_run_dir = tmp_path / "wandb_run_dir"
    wandb_run_dir.mkdir()
    return wandb_run_dir


@pytest.fixture
def wandb_init_run(wandb_run_dir):
    run = wandb.init(
        project="tree-gan",
        id=wandb.util.generate_id(),
        entity="bugan",
        anonymous="allow",
        mode="disabled",
        dir=wandb_run_dir,
    )
    return run


### CHECK FORWARD


def test_vaegan_forward(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = VAEGAN(config).to(device)
    x = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1]


def test_vae_forward(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = VAE_train(config).to(device)
    x = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1, 32, 32, 32]


def test_gan_forward(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = GAN(config).to(device)
    x = torch.tensor(np.ones([2, 2], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1]


def test_gan_wloss_forward(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = GAN_Wloss(config).to(device)
    x = torch.tensor(np.ones([2, 2], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1]


def test_gan_wloss_gp_forward(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = GAN_Wloss_GP(config).to(device)
    x = torch.tensor(np.ones([2, 2], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1]


def test_cgan_forward(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        num_classes=3,
    )
    model = CGAN(config).to(device)
    x = torch.tensor(np.ones([2, 2], dtype=np.float32)).to(device)
    c = torch.tensor(np.ones([2], dtype=np.int64)).to(device)
    y, c_predict = model(x, c)
    assert list(y.shape) == [2, 1]
    assert list(c_predict.shape) == [2, config.num_classes]


def test_cvaegan_forward(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        num_classes=3,
    )

    model = CVAEGAN(config).to(device)
    x = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    c = torch.tensor(np.ones([2], dtype=np.int64)).to(device)
    y, c_predict = model(x, c)
    assert list(y.shape) == [2, 1]
    assert list(c_predict.shape) == [2, config.num_classes]


def test_zvaegan_forward(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        num_classes=3,
    )

    model = ZVAEGAN(config).to(device)
    x = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    y = model(x)
    assert list(y.shape) == [2, 1]


### CHECK TRAINING STEP


def test_vaegan_training_step(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        fc_size=[2, 1, 2],
        z_size=2,
    )
    model = VAEGAN(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    model.on_train_epoch_start()
    loss_vae = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=0)
    loss_d = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=1)
    # tensor with single element has shape []
    assert list(loss_vae.shape) == [] and not loss_vae.isnan() and not loss_vae.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()


def test_vae_training_step(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = VAE_train(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    model.on_train_epoch_start()
    loss_vae = model.training_step(dataset_batch=[data], batch_idx=0)
    # tensor with single element has shape []
    assert list(loss_vae.shape) == [] and not loss_vae.isnan() and not loss_vae.isinf()


def test_gan_training_step(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        batch_size=1,
    )
    model = GAN(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    model.on_train_epoch_start()
    loss_g = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=0)
    loss_d = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=1)
    # tensor with single element has shape []
    assert list(loss_g.shape) == [] and not loss_g.isnan() and not loss_g.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()


def test_gan_wloss_training_step(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = GAN_Wloss(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    model.on_train_epoch_start()
    loss_g = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=0)
    loss_d = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=1)
    # tensor with single element has shape []
    assert list(loss_g.shape) == [] and not loss_g.isnan() and not loss_g.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()


def test_gan_wloss_gp_training_step(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
    )
    model = GAN_Wloss_GP(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    model.on_train_epoch_start()
    loss_g = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=0)
    loss_d = model.training_step(dataset_batch=[data], batch_idx=0, optimizer_idx=1)
    # tensor with single element has shape []
    assert list(loss_g.shape) == [] and not loss_g.isnan() and not loss_g.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()


def test_cgan_training_step(device):
    config = Namespace(
        resolution=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        num_classes=3,
    )
    model = CGAN(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    label = torch.tensor(np.ones([2], dtype=np.int64)).to(device)
    model.on_train_epoch_start()
    loss_g = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=0
    )
    loss_d = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=1
    )
    loss_c = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=2
    )
    # tensor with single element has shape []
    assert list(loss_g.shape) == [] and not loss_g.isnan() and not loss_g.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()
    assert list(loss_c.shape) == [] and not loss_c.isnan() and not loss_c.isinf()


def test_cvaegan_training_step(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        z_size=2,
        num_classes=3,
    )
    model = CVAEGAN(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    label = torch.tensor(np.ones([2], dtype=np.int64)).to(device)
    model.on_train_epoch_start()
    loss_vae = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=0
    )
    loss_d = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=1
    )
    loss_c = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=2
    )
    # tensor with single element has shape []
    assert list(loss_vae.shape) == [] and not loss_vae.isnan() and not loss_vae.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()
    assert list(loss_c.shape) == [] and not loss_c.isnan() and not loss_c.isinf()


def test_zvaegan_training_step(device):
    config = Namespace(
        resolution=32,
        encoder_num_layer_unit=[2, 2, 2, 2, 2],
        decoder_num_layer_unit=[2, 2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
        fc_size=[2, 1, 2],
        z_size=2,
    )
    model = ZVAEGAN(config).to(device)
    data = torch.tensor(np.ones([2, 1, 32, 32, 32], dtype=np.float32)).to(device)
    label = torch.tensor(np.ones([2], dtype=np.int64)).to(device)
    label[1] = -1
    model.on_train_epoch_start()
    loss_vae = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=0
    )
    loss_d = model.training_step(
        dataset_batch=[data, label], batch_idx=0, optimizer_idx=1
    )
    # tensor with single element has shape []
    assert list(loss_vae.shape) == [] and not loss_vae.isnan() and not loss_vae.isinf()
    assert list(loss_d.shape) == [] and not loss_d.isnan() and not loss_d.isinf()


### CHECK FULL TRAINING (with data_module, model, and trainer)


@pytest.fixture
def data_module(isConditionalData, config, wandb_init_run, data_path, tmp_path):
    return DataModule_process(
        config,
        data_path=data_path,
        tmp_folder=tmp_path / "datamodule_tmp_dir",
    )


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            encoder_num_layer_unit=[2, 2, 2, 2, 2],
            decoder_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("isConditionalData", [True])
@pytest.mark.parametrize("data_process_format", ["zip"])
def test_vaegan_training_loop_full(device, config, data_module):
    model = VAEGAN(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            encoder_num_layer_unit=[2, 2, 2, 2, 2],
            decoder_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_vae_training_loop_full(device, config, data_module):
    model = VAE_train(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            gen_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_gan_training_loop_full(device, config, data_module):
    model = GAN(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            gen_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_gan_wloss_training_loop_full(device, config, data_module):
    model = GAN_Wloss(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            gen_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_gan_wloss_gp_training_loop_full(device, config, data_module):
    model = GAN_Wloss_GP(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            gen_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            num_classes=1,
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_cgan_training_loop_full(device, config, data_module):
    model = CGAN(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            encoder_num_layer_unit=[2, 2, 2, 2, 2],
            decoder_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            num_classes=1,
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_cvaegan_training_loop_full(device, config, data_module):
    model = CVAEGAN(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


@pytest.mark.parametrize(
    "config",
    [
        Namespace(
            resolution=32,
            encoder_num_layer_unit=[2, 2, 2, 2, 2],
            decoder_num_layer_unit=[2, 2, 2, 2, 2],
            dis_num_layer_unit=[2, 2, 2, 2, 2],
            z_size=2,
            # for dataloader
            batch_size=1,
            data_augmentation=True,
            aug_rotation_type="random rotation",
            aug_rotation_axis=(0, 1, 0),
            num_classes=1,
            log_interval=1,
        )
    ],
)
@pytest.mark.parametrize("data_process_format", ["zip"])
@pytest.mark.parametrize("isConditionalData", [True])
def test_zvaegan_training_loop_full(device, config, data_module):
    model = ZVAEGAN(config).to(device)
    trainer = pl.Trainer(max_epochs=1)
    trainer.fit(model, data_module)


### TEST EXPERIMENT SCRIPT
@pytest.mark.parametrize("data_process_format", ["folder", "zip"])
@pytest.mark.parametrize("isConditionalData", [False])
# resume_id: "1iqrmh7p" (github build test fail as wandb API key not set)
@pytest.mark.parametrize("resume_id", [""])
def test_trainPL_script(data_path, tmp_path, resume_id):
    config_dict = dict(
        aug_rotation_type="random rotation",
        data_augmentation=True,
        aug_rotation_axis=(0, 1, 0),
        data_location=str(data_path),
        selected_model="GAN",
        log_interval=1,
        log_num_samples=1,
        project_name="tree-gan",
        resolution=32,
        num_classes=0,
        seed=1234,
        epochs=1,
        batch_size=32,
        gen_num_layer_unit=[2, 2, 2, 2, 2],
        dis_num_layer_unit=[2, 2, 2, 2, 2],
    )
    config = Namespace(**config_dict)
    # also test resume_id
    config.resume_id = resume_id

    dataset_path = Path(config.data_location)
    if str(config.data_location).endswith(".zip"):
        config.dataset = dataset_path.stem
    else:
        config.dataset = "dataset_array_custom"

    # get previous config if resume run
    if config.resume_id:
        project_name = config.project_name
        resume_id = config.resume_id
        prev_config = get_resume_run_config(project_name, resume_id)
        # replace config with prev_config
        config = vars(config)
        config.update(vars(prev_config))
        config = Namespace(**config)

    # write bugan package revision number to bugan
    config.rev_number = get_bugan_package_revision_number()

    run_dir = tmp_path / "wandb_run_dir"
    run_dir.mkdir()
    run, config = init_wandb_run(config, run_dir=run_dir, mode="offline")
    dataModule = setup_datamodule(
        config,
        tmp_folder=tmp_path / "datamodule_tmp_dir",
    )

    model, extra_trainer_args = setup_model(config, run)

    if torch.cuda.is_available():
        extra_trainer_args["gpus"] = None

    # test save/load config
    config = setup_config_arguments(config)
    save_model_args(config, run)
    filepath = str(Path(run.dir).absolute() / "model_args.json")
    loaded = load_model_args(filepath)

    assert loaded.z_size == config.z_size

    train(config, run, model, dataModule, extra_trainer_args)

    # finish the run in tests, so the next test won't be affected
    run.finish()

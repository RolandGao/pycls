#!/usr/bin/env python3

# Copyright (c) Facebook, Inc. and its affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

"""Functions that handle saving and loading of checkpoints."""

import os
from shutil import copyfileobj

import pycls.core.distributed as dist
import torch
from iopath.common.file_io import g_pathmgr
from pycls.core.config import cfg
from pycls.core.net import unwrap_model


# Common prefix for checkpoint file names
#_NAME_PREFIX = "model_epoch_"

# Checkpoints directory name
_DIR_NAME = "checkpoints"


def get_checkpoint_dir():
    """Retrieves the location for storing checkpoints."""
    return os.path.join(cfg.OUT_DIR, _DIR_NAME)


# def get_checkpoint(epoch):
#     """Retrieves the path to a checkpoint file."""
#     name = "{}{:04d}.pyth".format(_NAME_PREFIX, epoch)
#     return os.path.join(get_checkpoint_dir(), name)
def get_last_checkpoint():
    """Retrieves the path to a checkpoint file."""
    name = "last_model.pyth"
    return os.path.join(get_checkpoint_dir(), name)

def get_best_checkpoint():
    """Retrieves the path to the best checkpoint file."""
    return os.path.join(get_checkpoint_dir(), "best_model.pyth")


def has_checkpoint():
    """Determines if there are checkpoints available."""
    checkpoint_dir = get_checkpoint_dir()
    if not g_pathmgr.exists(checkpoint_dir):
        return False
    return any("last_model.pyth" in f for f in g_pathmgr.ls(checkpoint_dir))


def save_checkpoint(model, optimizer, epoch, best):
    """Saves a checkpoint."""
    # Save checkpoints only from the master process
    if not dist.is_master_proc():
        return
    # Ensure that the checkpoint dir exists
    g_pathmgr.mkdirs(get_checkpoint_dir())
    # Record the state
    checkpoint = {
        "epoch": epoch,
        "model_state": unwrap_model(model).state_dict(),
        "optimizer_state": optimizer.state_dict(),
        "cfg": cfg.dump(),
    }
    # Write the checkpoint
    checkpoint_file = get_last_checkpoint()
    with g_pathmgr.open(checkpoint_file, "wb") as f:
        torch.save(checkpoint, f)
    # If best copy checkpoint to the best checkpoint
    if best:
        with g_pathmgr.open(checkpoint_file, "rb") as src:
            with g_pathmgr.open(get_best_checkpoint(), "wb") as dst:
                copyfileobj(src, dst)
    return checkpoint_file


def load_checkpoint(checkpoint_file, model, optimizer=None):
    """Loads the checkpoint from the given file."""
    err_str = "Checkpoint '{}' not found"
    assert g_pathmgr.exists(checkpoint_file), err_str.format(checkpoint_file)
    with g_pathmgr.open(checkpoint_file, "rb") as f:
        checkpoint = torch.load(f, map_location="cpu")
    unwrap_model(model).load_state_dict(checkpoint["model_state"])
    optimizer.load_state_dict(checkpoint["optimizer_state"]) if optimizer else ()
    return checkpoint["epoch"]

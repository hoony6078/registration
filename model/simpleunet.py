# -*- coding: future_fstrings -*-
import torch
import torch.nn as nn
import MinkowskiEngine as ME
import MinkowskiEngine.MinkowskiFunctional as MEF
from model.common import get_norm
from model.residual_block import get_block


class SimpleNet(ME.MinkowskiNetwork):
  NORM_TYPE = 'BN'
  BLOCK_NORM_TYPE = 'BN'
  CHANNELS = [None, 32, 64, 128]
  TR_CHANNELS = [None, 32, 32, 64]

  # To use the model, must call initialize_coords before forward pass.
  # Once data is processed, call clear to reset the model before calling initialize_coords
  
  def __init__(self,
        in_channels=1,
        out_channels=1,
        bn_momentum=0.09,
        normalize_feature=None,
        conv1_kernel_size=3,
        D=3
    ):

    super(SimpleNet, self).__init__(D)
    NORM_TYPE = self.NORM_TYPE
    CHANNELS = self.CHANNELS
    TR_CHANNELS = self.TR_CHANNELS
    BLOCK_NORM_TYPE = self.BLOCK_NORM_TYPE

    self.normalize_feature = normalize_feature

    self.conv1 = ME.MinkowskiConvolution(
        in_channels=in_channels,
        out_channels=CHANNELS[1],
        kernel_size=conv1_kernel_size,
        stride=1,
        dilation=1,
        bias=False,
        dimension=D)

    self.norm1 = get_norm(NORM_TYPE, CHANNELS[1], bn_momentum=bn_momentum, D=D)

    self.block1 = get_block(
        BLOCK_NORM_TYPE, CHANNELS[1], CHANNELS[1], bn_momentum=bn_momentum, D=D)

    self.conv2 = ME.MinkowskiConvolution(
        in_channels=CHANNELS[1],
        out_channels=CHANNELS[2],
        kernel_size=3,
        stride=2,
        dilation=1,
        bias=False,
        dimension=D)
    self.norm2 = get_norm(NORM_TYPE, CHANNELS[2], bn_momentum=bn_momentum, D=D)

    self.block2 = get_block(
        BLOCK_NORM_TYPE, CHANNELS[2], CHANNELS[2], bn_momentum=bn_momentum, D=D)

    self.conv3 = ME.MinkowskiConvolution(
        in_channels=CHANNELS[2],
        out_channels=CHANNELS[3],
        kernel_size=3,
        stride=2,
        dilation=1,
        bias=False,
        dimension=D)
    self.norm3 = get_norm(NORM_TYPE, CHANNELS[3], bn_momentum=bn_momentum, D=D)

    self.block3 = get_block(
        BLOCK_NORM_TYPE, CHANNELS[3], CHANNELS[3], bn_momentum=bn_momentum, D=D)

    self.conv3_tr = ME.MinkowskiConvolutionTranspose(
        in_channels=CHANNELS[3],
        out_channels=TR_CHANNELS[3],
        kernel_size=3,
        stride=2,
        dilation=1,
        bias=False,
        dimension=D)
    self.norm3_tr = get_norm(NORM_TYPE, TR_CHANNELS[3], bn_momentum=bn_momentum, D=D)

    self.block3_tr = get_block(
        BLOCK_NORM_TYPE, TR_CHANNELS[3], TR_CHANNELS[3], bn_momentum=bn_momentum, D=D)

    self.conv2_tr = ME.MinkowskiConvolutionTranspose(
        in_channels=CHANNELS[2] + TR_CHANNELS[3],
        out_channels=TR_CHANNELS[2],
        kernel_size=3,
        stride=2,
        dilation=1,
        bias=False,
        dimension=D)
    self.norm2_tr = get_norm(NORM_TYPE, TR_CHANNELS[2], bn_momentum=bn_momentum, D=D)

    self.block2_tr = get_block(
        BLOCK_NORM_TYPE, TR_CHANNELS[2], TR_CHANNELS[2], bn_momentum=bn_momentum, D=D)

    self.conv1_tr = ME.MinkowskiConvolution(
        in_channels=CHANNELS[1] + TR_CHANNELS[2],
        out_channels=TR_CHANNELS[1],
        kernel_size=3,
        stride=1,
        dilation=1,
        bias=False,
        dimension=D)
    self.norm1_tr = get_norm(NORM_TYPE, TR_CHANNELS[1], bn_momentum=bn_momentum, D=D)

    self.final = ME.MinkowskiConvolution(
        in_channels=TR_CHANNELS[1],
        out_channels=out_channels,
        kernel_size=1,
        stride=1,
        dilation=1,
        bias=True,
        dimension=D)
    
  def forward(self, x):
    out_s1 = self.conv1(x)
    out_s1 = self.norm1(out_s1)
    out_s1 = self.block1(out_s1)
    out = MEF.relu(out_s1)

    out_s2 = self.conv2(out)
    out_s2 = self.norm2(out_s2)
    out_s2 = self.block2(out_s2)
    out = MEF.relu(out_s2)

    out_s4 = self.conv3(out)
    out_s4 = self.norm3(out_s4)
    out_s4 = self.block3(out_s4)
    out = MEF.relu(out_s4)

    out = self.conv3_tr(out)
    out = self.norm3_tr(out)
    out = self.block3_tr(out)
    out_s2_tr = MEF.relu(out)

    out = ME.cat(out_s2_tr, out_s2)

    out = self.conv2_tr(out)
    out = self.norm2_tr(out)
    out = self.block2_tr(out)
    out_s1_tr = MEF.relu(out)

    out = ME.cat(out_s1_tr, out_s1)
    out = self.conv1_tr(out)
    out = self.norm1_tr(out)
    out = MEF.relu(out)

    out = self.final(out)

    if self.normalize_feature:
      return ME.SparseTensor(
          out.F / torch.norm(out.F, p=2, dim=1, keepdim=True),
          coordinate_map_key=out.coordinate_map_key,
          coordinate_manager=out.coordinate_manager)
    else:
      return out
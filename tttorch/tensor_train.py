import torch
import numpy as np


class TensorTrain(object):
    def __init__(self, tt_cores, shape=None, tt_ranks=None, convert_to_tensors=True):
        tt_cores = list(tt_cores)
        if convert_to_tensors:
            for i in range(len(tt_cores)):
                tt_cores[i] = torch.Tensor(tt_cores[i])

        self._tt_cores = tuple(tt_cores)

        if len(self._tt_cores[0].shape) == 4:
            self._is_tt_matrix = True
        else:
            self._is_tt_matrix = False

        if self._is_tt_matrix:
            self._raw_shape = [[tt_core.shape[1] for tt_core in self._tt_cores],
                               [tt_core.shape[2] for tt_core in self._tt_cores]]
            self._shape = [int(np.prod(self._raw_shape[0])), int(np.prod(self._raw_shape[1]))]
            self._ndims = len(self._raw_shape[0])

        else:
            self._raw_shape = [tt_core.shape[1] for tt_core in self._tt_cores]
            self._shape = [tt_core.shape[1] for tt_core in self._tt_cores]
            self._ndims = len(self._raw_shape)

        self._ranks = [tt_core.shape[0] for tt_core in self._tt_cores] + [1, ]

    @property
    def tt_cores(self):
        """A list of TT-cores.
        Returns:
          A list of 3d or 4d tensors of shape
        """
        return self._tt_cores

    @property
    def raw_shape(self):
        return self._raw_shape

    @property
    def is_tt_matrix(self):
        return self._is_tt_matrix

    @property
    def shape(self):
        return self._shape

    @property
    def ranks(self):
        return self._ranks

    @property
    def ndims(self):
        return self._ndims

    def to(self, device):
        for core in self.cores:
            core.to(device)

    def full(self):
        num_dims = self.ndims
        ranks = self.ranks
        shape = self.shape
        raw_shape = self.raw_shape
        res = self.tt_cores[0]

        for i in range(1, num_dims):
            res = res.contiguous().view(-1, ranks[i])
            curr_core = self.tt_cores[i].contiguous().view(ranks[i], -1)
            res = torch.matmul(res, curr_core)

        if self.is_tt_matrix:
            intermediate_shape = []
            for i in range(num_dims):
                intermediate_shape.append(raw_shape[0][i])
                intermediate_shape.append(raw_shape[1][i])

            res = res.view(*intermediate_shape)
            transpose = []
            for i in range(0, 2 * num_dims, 2):
                transpose.append(i)
            for i in range(1, 2 * num_dims, 2):
                transpose.append(i)
            res = res.permute(*transpose)

        res = res.contiguous().view(*shape)
        return res


class TensorTrainBatch():
    def __init__(self, tt_cores, shape=None, tt_ranks=None, convert_to_tensors=True):
        tt_cores = list(tt_cores)
        if convert_to_tensors:
            for i in range(len(tt_cores)):
                tt_cores[i] = torch.Tensor(tt_cores[i])

        self._tt_cores = tuple(tt_cores)

        self._batch_size = self._tt_cores[0].shape[0]

        if len(self._tt_cores[0].shape) == 5:
            self._is_tt_matrix = True
        else:
            self._is_tt_matrix = False

        if self._is_tt_matrix:
            self._raw_shape = [[tt_core.shape[2] for tt_core in self._tt_cores],
                               [tt_core.shape[3] for tt_core in self._tt_cores]]
            self._shape = [self._batch_size, int(
                np.prod(self._raw_shape[0])), int(np.prod(self._raw_shape[1]))]
            self._ndims = len(self._raw_shape[0])

        else:
            self._raw_shape = [tt_core.shape[2] for tt_core in self._tt_cores]
            self._shape = [self._batch_size, ] + [tt_core.shape[2] for tt_core in self._tt_cores]
            self._ndims = len(self._raw_shape)

        self._ranks = [tt_core.shape[1] for tt_core in self._tt_cores] + [1, ]

    @property
    def tt_cores(self):
        """A list of TT-cores.
        Returns:
          A list of 4d or 5d tensors.
        """
        return self._tt_cores

    @property
    def raw_shape(self):
        return self._raw_shape

    @property
    def is_tt_matrix(self):
        return self._is_tt_matrix

    @property
    def shape(self):
        return self._shape

    @property
    def ranks(self):
        return self._ranks

    @property
    def ndims(self):
        return self._ndims

    @property
    def batch_size(self):
        return self._batch_size

    def to(self, device):
        for core in self.cores:
            core.to(device)

    def full(self):
        num_dims = self.ndims
        ranks = self.ranks
        shape = self.shape
        raw_shape = self.raw_shape
        res = self.tt_cores[0]
        batch_size = self.batch_size

        for i in range(1, num_dims):
            res = res.view(batch_size, -1, ranks[i])
            curr_core = self.tt_cores[i].view(batch_size, ranks[i], -1)
            res = torch.einsum('oqb,obw->oqw', (res, curr_core))

        if self.is_tt_matrix:
            intermediate_shape = [batch_size]
            for i in range(num_dims):
                intermediate_shape.append(raw_shape[0][i])
                intermediate_shape.append(raw_shape[1][i])
            res = res.view(*intermediate_shape)
            transpose = [0]
            for i in range(0, 2 * num_dims, 2):
                transpose.append(i + 1)
            for i in range(1, 2 * num_dims, 2):
                transpose.append(i + 1)
            res = res.permute(transpose)
        res = res.contiguous().view(*shape)
        return res
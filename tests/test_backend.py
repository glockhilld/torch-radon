from .utils import generate_random_images, relative_error, circle_mask
from .astra_wrapper import AstraWrapper
from nose.tools import assert_less, assert_equal
import torch
import numpy as np
from torch_radon import Radon
from parameterized import parameterized

device = torch.device('cuda')

full_angles = np.linspace(0, 2 * np.pi, 180).astype(np.float32)
limited_angles = np.linspace(0.2 * np.pi, 0.5 * np.pi, 50).astype(np.float32)
sparse_angles = np.linspace(0, 2 * np.pi, 18).astype(np.float32)

params = []  # [(device, 8, 128, full_angles)]
for batch_size in [1, 8, 16, 32]:  # , 64, 128]:  # , 256, 512]:
    for image_size in [128, 256]:  # , 512]:
        for angles in [full_angles, limited_angles, sparse_angles]:
            params.append((device, batch_size, image_size, angles))


@parameterized(params)
def test_error(device, batch_size, image_size, angles):
    # generate random images
    x = generate_random_images(batch_size, image_size)

    # astra
    astra = AstraWrapper(angles)

    astra_fp_id, astra_fp = astra.forward(x)
    astra_bp = astra.backproject(astra_fp_id, image_size, batch_size)
    astra_bp *= circle_mask(image_size)

    # our implementation
    radon = Radon(image_size)
    x = torch.FloatTensor(x).to(device)
    angles = torch.FloatTensor(angles).to(device)

    our_fp = radon.forward(x, angles)
    our_bp = radon.backprojection(our_fp, angles)

    forward_error = relative_error(astra_fp, our_fp.cpu().numpy())
    back_error = relative_error(astra_bp, our_bp.cpu().numpy())

    print(batch_size, image_size, forward_error, back_error)
    assert_less(forward_error, 1e-2)
    assert_less(back_error, 5e-3)


def test_noise():
    x = torch.FloatTensor(3, 5, 64, 64).to(device)
    lookup_table = torch.FloatTensor(128, 64).to(device)
    x.requires_grad = True
    angles = torch.FloatTensor(np.linspace(0, 2 * np.pi, 10).astype(np.float32)).to(device)

    radon = Radon(64, device)

    sinogram = radon.forward(x, angles)
    assert_equal(sinogram.size(), (3, 5, 10, 64))

    readings = radon.emulate_readings(sinogram, 5, 10.0)
    assert_equal(readings.size(), (3, 5, 10, 64))
    assert_equal(readings.dtype, torch.int32)

    y = radon.readings_lookup(readings, lookup_table)
    assert_equal(y.size(), (3, 5, 10, 64))
    assert_equal(y.dtype, torch.float32)



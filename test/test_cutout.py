import os
import sys

from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np
import pandas as pd
import pytest
import unittest

sys.path.append('..')
from cutout import CutoutProducer

class TestRaise(unittest.TestCase):
    def test_import_raise(self):
        with self.assertRaises(OSError):
            dummy_cutout_producer = CutoutProducer(tilename='i_dont_exist',
                                                   cutout_size=45,
                                                   psf_cutout_size=45,
                                                   metadata_path='test_data/')
            dummy_cutout_producer.read_metadata()

    def test_no_tile_raise(self):
        with self.assertRaises(ValueError):
            dummy_cutout_producer = CutoutProducer(tilename='i_dont_exist',
                                                   cutout_size=45,
                                                   psf_cutout_size=45,
                                                   metadata_path='test_data/')
            dummy_filename = dummy_cutout_producer.get_tile_filename('g')

    def test_multiple_tiles_raise(self):
        with self.assertRaises(ValueError):
            dummy_cutout_producer = CutoutProducer(tilename='multiple_tiles',
                                                   cutout_size=45,
                                                   psf_cutout_size=45,
                                                   metadata_path='test_data/')
            dummy_filename = dummy_cutout_producer.get_tile_filename('g')


class TestCutoutProducer(unittest.TestCase):
    def setUp(self):
        self.cutout_producer = CutoutProducer(tilename='testtile', cutout_size=45,
                                              psf_cutout_size=45,
                                              bands='grizY',
                                              metadata_path='test_data/',
                                              coadds_path='test_data/',
                                              psf_path='test_data/')

    def test_read_metadata(self):
        self.cutout_producer.read_metadata()
        self.assertTrue(hasattr(self.cutout_producer, "metadata"))
        self.assertTrue(isinstance(self.cutout_producer.metadata, pd.core.frame.DataFrame))

    def test_get_tile_filename(self):
        for band in self.cutout_producer.bands:
            tile_filename = self.cutout_producer.get_tile_filename(band)
            self.assertEqual(tile_filename, 'test_data/testtile_r_123_{band}.fitz.fz')
            self.assertTrue(os.path.exists(tile_filename))

    def test_get_tile_psf_filename(self):
        for band in self.cutout_producer.bands:
            psf_filename = self.cutout_producer.get_tile_filename(band)
            self.assertEqual(psf_filename, f'test_data/testtile/testtile_r123_{band}.psfcat.psf')
            self.assertTrue(os.path.exists(tile_filename))

    def test_read_tile_image(self):
        for band in self.cutout_producer.bands:
            tile_filename = self.cutout_producer.get_tile_filename(band)
            image, wcs = self.cutout_producer.read_tile_image(band)
            self.assertEqual(len(np.shape(image)), 2)
            self.assertIsInstance(wcs, astropy.wcs.WCS)

    def test_get_locations(self):
        ras, decs = self.cutout_producer.get_locations()
        self.assertEqual(len(ras), len(decs))
        self.assertIsInstance(ras, np.ndarray)
        self.assertIsInstance(decs, np.ndarray)
        self.assertEqual(ras.dtype, float)
        self.assertEqual(decs.dtype, float)
        self.assertGreaterEqual(ras.min(), 0.0)
        self.assertLessEqual(ras.max(), 360.0)
        self.assertGreaterEqual(decs.min(), -90.0)
        self.assertLessEqual(decs.max(), 90.0)

    def test_get_coadd_ids(self):
        self.cutout_producer.get_coadd_ids()
        self.assertIsInstance(self.cutout_producer.coadd_ids, np.ndarray)
        self.assertEqual(len(self.cutout_producer.coadd_ids), len(self.cutout_producer.metadata))
        self.assertEqual(self.cutout_producer.coadd_ids.dtype, int)

    def test_get_object_xy(self):
        self.cutout_producer.get_coadd_ids()
        image, wcs = self.cutout_producer.read_tile_image('g')
        object_x, object_y = self.cutout_producer.get_object_xy(wcs)
        self.assertEqual(len(object_x), len(self.cutout_producer.coadd_ids))
        self.assertEqual(len(object_y), len(object_x))
        self.assertIsInstance(object_x, np.ndarray)
        self.assertIsInstance(object_y, np.ndarray)
        self.assertIsInstance(object_x[0], int)
        self.assertIsInstance(object_y[0], int)

    def test_cutout_objects(self):
        self.cutout_producer.get_coadd_ids()
        image, wcs = self.cutout_producer.read_tile_image('g')
        cutouts = self.cutout_producer.cutout_objects(image, wcs)
        self.assertIsInstance(cutouts, np.ndarray)
        self.assertEqual(np.shape(cutouts)[0], len(self.cutout_producer.coadd_ids))
        self.assertEqual(np.shape(cutouts)[1], len(self.cutout_producer.cutout_size))
        self.assertEqual(np.shape(cutouts)[2], len(self.cutout_producer.cutout_size))
        self.assertEqual(len(np.shape(cutouts)), 3)
        self.assertIsInstance(cutouts[0][0][0], (float, int))

    def test_single_cutout(self):
        image, wcs = self.cutout_producer.read_tile_image('g')
        object_x, object_y = self.cutout_producer.get_object_xy(wcs)
        center = (object_x[0], object_y[0])
        cutout = self.cutout_producer.single_cutout(image, center)
        self.assertIsInstance(cutout, np.ndarray)
        self.assertEqual(len(np.shape(cutout)), 2)
        self.assertEqual(np.shape(cutout)[0], self.cutout_producer.cutout_size)
        self.assertEqual(np.shape(cutout)[1], self.cutout_producer.cutout_size)

        # test with width argument
        width = 15
        cutout = self.cutout_producer.single_cutout(image, center, width=width)
        self.assertIsInstance(cutout, np.ndarray)
        self.assertEqual(len(np.shape(cutout)), 2)
        self.assertEqual(np.shape(cutout)[0], width)
        self.assertEqual(np.shape(cutout)[1], width)

        raise NotImplementedError("I'd like to test that the pixel values in the cutout"
                                  "match up with the pixel values in the image")

    def test_cutout_psfs(self):
        self.cutout_producer.get_coadd_ids()
        image, wcs = self.cutout_producer.read_tile_image('g')
        psf_cutouts = self.cutout_producer.cutout_psfs(wcs)
        self.assertEqual(len(np.shape(psf_cutouts)), 3)
        self.assertEqual(np.shape(psf_cutouts)[0], len(self.cutout_producer.coadd_ids))
        self.assertEqual(np.shape(psf_cutouts)[1], self.cutout_producer.psf_cutout_size)
        self.assertEqual(np.shape(psf_cutouts)[2], self.cutout_producer.psf_cutout_size)

    def test_combine_bands(self):
        image_array, psf_array = self.cutout_producer.combine_bands()
        self.assertEqual(len(np.shape(image_array)), 4)
        self.assertEqual(np.shape(image_array)[0], len(self.cutout_producer.coadd_ids))
        self.assertEqual(np.shape(image_array)[1], len(self.cutout_producer.bands))
        self.assertEqual(np.shape(image_array)[2], len(self.cutout_producer.cutout_size))
        self.assertEqual(np.shape(image_array)[3], len(self.cutout_producer.cutout_size))

        self.assertEqual(len(np.shape(psf_array)), 4)
        self.assertEqual(np.shape(psf_array)[0], len(self.cutout_producer.coadd_ids))
        self.assertEqual(np.shape(psf_array)[1], len(self.cutout_producer.bands))
        self.assertEqual(np.shape(psf_array)[2], len(self.cutout_producer.psf_cutout_size))
        self.assertEqual(np.shape(psf_array)[3], len(self.cutout_producer.psf_cutout_size))

    def test_produce_cutout_file(self):
        image_array, psf_array = self.cutout_producer.combine_bands()
        self.cutout_producer.produce_cutout_file(image_array, psf_array, outdir="test_data/")
        outfile_name = f'test_data/{self.cutout_producer.tilename}.fits'

        self.assertTrue(os.path.exists(outfile_name))

        raise NotImplementedError("Open the fits file and check that everything looks good")


if __name__ == "__main__":
    pytest.main()

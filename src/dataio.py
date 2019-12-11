## @package dataio
#  This package handles the interface with the hard drive.
#
#  It can in particular read and write matlab or python matrices.
import numpy as np
import logging as log
import fnmatch
import sys
import os
import plot
import tensorflow as tf
import scipy.io
import random
from collections import Counter
from scipy.stats import zscore
import matplotlib.pyplot as plt
import ipdb
from plot import plot_aug_examples
logger = log.getLogger("classifier")
from sklearn.model_selection import train_test_split
import pandas as pd



def find_files(directory, pattern='*.csv'):
    files = []
    for root, dirnames, filenames in os.walk(directory):
        for filename in fnmatch.filter(filenames, pattern):
            files.append(os.path.join(root, filename))

    return files


def get_val_data(labels, ids, num_val, spectra, train_test, validate, class_id=0, fold=0):
    """
    Get fixed ratio of val data from different numbers of each class
    :param labels: array
    :param ids: a
    :param num_val: int
    :param spectra: array
    :param train_test: dict, "features", "labels", "ids"
    :param validate: dict, with "features", "labels", "ids"
    :param class_id: the id of the class
    :return:
    """

    indices = np.where(labels == class_id)[0]
    random.shuffle(indices)
    val_inds = indices[fold*np.int(num_val): (fold+1)*np.int(num_val)]
    train_test_inds = indices[np.int(num_val):]
    train_test["features"] = np.vstack((train_test["features"], spectra[train_test_inds, :]))
    train_test["labels"] = np.append(train_test["labels"], labels[train_test_inds])
    train_test["ids"] = np.append(train_test["ids"], ids[train_test_inds])

    validate["features"] = np.vstack((validate["features"], spectra[val_inds, :]))
    validate["labels"] = np.append(validate["labels"],labels[val_inds])
    validate["ids"] = np.append(validate["ids"], ids[val_inds])

    return train_test, validate


def pick_lout_ids(ids, count, num_lout=1, start=0):
    """
    Leave out several subjects for validation
    :param labels:
    :param ids:
    :param leave_out_id:
    :param spectra:
    :param train_test:
    :param validate:
    :return:
    Use it at the first time to get a overview of the data distribution. sorted_count = sorted(count.items(), key=lambda kv: kv[1])
    # np.savetxt("../data/20190325/20190325_count.csv", np.array(sorted_count), fmt="%.1f", delimiter=',')
    """
      # count the num of samples of each id
    if start == 9:
        lout_ids = list(count.keys())[num_lout*start :]
    else:
        lout_ids = list(count.keys())[num_lout * start: num_lout * (start + 1)]
    # np.savetxt("../data/lout_ids_{}.csv".format(start), np.array(lout_ids), fmt="%.1f", delimiter=',')
    return lout_ids


def split_data_for_lout_val(args):
    """
    Split the original data in leave several subjects
    :param args:
    :return: save two .mat files
    """
    mat = scipy.io.loadmat(args.input_data)["DATA"]
    spectra = mat[:, 2:]
    labels = mat[:, 1]  ##20190325-9243 samples, 428 patients
    ids = mat[:, 0]

    count = dict(Counter(list(ids)))

    for i in range(len(count) // args.num_lout):
        validate = {}
        validate["features"] = np.empty((0, 288))
        validate["labels"] = np.empty((0))
        validate["ids"] = np.empty((0))

        lout_ids = pick_lout_ids(ids, count, num_lout=args.num_lout, start=i)  # leave 10 subjects out

        all_inds = np.empty((0))
        for id in lout_ids:
            inds = np.where(ids == id)[0]
            all_inds = np.append(all_inds, inds)
            validate["features"] = np.vstack((validate["features"], spectra[inds, :]))
            validate["labels"] = np.append(validate["labels"], labels[inds])
            validate["ids"] = np.append(validate["ids"], ids[inds])
        train_test_data = np.delete(mat, all_inds, axis=0)  # delete all leaved-out subjects
        print("Leave out: \n", lout_ids, "\n num_lout\n", len(validate["labels"]))

        # ndData
        val_mat = {}
        train_test_mat = {}
        val_mat["DATA"] = np.zeros((validate["labels"].size, 290))
        val_mat["DATA"][:, 0] = validate["ids"]
        val_mat["DATA"][:, 1] = validate["labels"]
        val_mat["DATA"][:, 2:] = validate["features"]
        train_test_mat["DATA"] = np.zeros((len(train_test_data), 290))
        train_test_mat["DATA"][:, 0] = train_test_data[:, 0]
        train_test_mat["DATA"][:, 1] = train_test_data[:, 1]
        train_test_mat["DATA"][:, 2:] = train_test_data[:, 2:]
        print("num_train\n", len(train_test_mat["DATA"][:, 1]))
        scipy.io.savemat(os.path.dirname(args.input_data) + '/20190325-{}class_lout{}_val_data{}.mat'.format(args.num_classes, args.num_lout, i), val_mat)
        scipy.io.savemat(
            os.path.dirname(args.input_data) + '/20190325-{}class_lout{}_train_test_data{}.mat'.format(args.num_classes, args.num_lout, i), train_test_mat)


def split_data_for_val(args):
    """
    Split the original data into train_test set and validate set
    :param args:
    :return: save two .mat files
    """
    mat = scipy.io.loadmat(args.input_data)["DATA"]
    np.random.shuffle(mat)   # shuffle the data
    spectra = mat[:, 2:]
    labels = mat[:, 1]
    ids = mat[:, 0]

    num_val = ids.size // 10   # leave 100 samples from each class out
    for fold in range(10):
        train_test = {}
        validate = {}
        validate["features"] = np.empty((0, 288))
        validate["labels"] = np.empty((0))
        validate["ids"] = np.empty((0))
        train_test["features"] = np.empty((0, 288))
        train_test["labels"] = np.empty((0))
        train_test["ids"] = np.empty((0))

        if args.num_classes == 2:
            for class_id in range(args.num_classes):
                train_test, validate = get_val_data(labels, ids, num_val, spectra, train_test, validate, class_id=class_id, fold=fold)
        elif args.num_classes == 6:
            for class_id in range(args.num_classes):
                train_test, validate = get_val_data(labels, ids, num_val, spectra, train_test, validate, class_id=class_id, fold=fold)
        elif args.num_classes == 3: # ()
            for class_id in range(args.num_classes):
                train_test, validate = get_val_data(labels, ids, num_val, spectra, train_test, validate, class_id=class_id, fold=fold)
        ### ndData
        val_mat = {}
        train_test_mat = {}
        val_mat["DATA"] = np.zeros((validate["labels"].size, 290))
        val_mat["DATA"][:, 0] = validate["ids"]
        val_mat["DATA"][:, 1] = validate["labels"]
        val_mat["DATA"][:, 2:] = validate["features"]
        train_test_mat["DATA"] = np.zeros((train_test["labels"].size, 290))
        train_test_mat["DATA"][:, 0] = train_test["ids"]
        train_test_mat["DATA"][:, 1] = train_test["labels"]
        train_test_mat["DATA"][:, 2:] = train_test["features"]
        scipy.io.savemat(os.path.dirname(args.input_data) + '/{}class_val_rand_data{}.mat'.format(args.num_classes, fold), val_mat)
        scipy.io.savemat(os.path.dirname(args.input_data) + '/{}class_train_test_rand_data{}.mat'.format(args.num_classes, fold), train_test_mat)


def get_data(args):
    """
    Load self_saved data. A dict, data["features"], data["labels"]. See the save function in split_data_for_val()
    # First time preprocess data functions are needed: split_data_for_val(args),split_data_for_lout_val(args)
    :param args: Param object with path to the data
    :return:
    """
    mat = scipy.io.loadmat(args.input_data)["DATA"]
    labels = mat[:, 1]

    new_mat = np.zeros((mat.shape[0], mat.shape[1] + 1))
    new_mat[:, 0] = np.arange(mat.shape[0])   # tag every sample
    new_mat[:, 1:] = mat
    train_data = {}
    test_data = {}

    ## following code is to get only label 0 and 1 data from the file. TODO: to make this more easy and clear
    if args.num_classes - 1 < np.max(labels):
        sub_inds = np.empty((0))
        for class_id in range(args.num_classes):
            sub_inds = np.append(sub_inds, np.where(labels==class_id)[0])
        sub_inds = sub_inds.astype(np.int32)
        sub_mat = new_mat[sub_inds]
    else:
        sub_mat = new_mat

    np.random.shuffle(sub_mat)
    print("data labels: ", sub_mat[:, 2])

    if args.test_ratio == 100:
        X_train, X_test, Y_train, Y_test = [], sub_mat, [], sub_mat[:, 2]
    else:
        X_train, X_test, Y_train, Y_test = train_test_split(sub_mat, sub_mat[:, 2], test_size=args.test_ratio/100.)

    test_data["spectra"] = zscore(X_test[:, 3:], axis=1).astype(np.float32)
    test_data["labels"] = Y_test.astype(np.int32)
    assert np.sum(Y_test.astype(np.int32) == X_test[:, 2].astype(np.int32)) == len(
        X_test), "train_test_split messed up the data!"
    test_data["ids"] = X_test[:, 1].astype(np.int32)
    test_data["sample_ids"] = X_test[:, 0].astype(np.int32)
    test_data["num_samples"] = len(test_data["labels"])
    print("num_samples: ", test_data["num_samples"])
    #
    test_count = dict(Counter(list(test_data["ids"])))  # count the num of samples of each id
    sorted_count = sorted(test_count.items(), key=lambda kv: kv[1])
    np.savetxt(os.path.join(args.output_path, "test_ids_count.csv"), np.array(sorted_count), fmt='%d',
               delimiter=',')
    np.savetxt(os.path.join(args.output_path, "original_labels.csv"), np.array(test_data["labels"]), fmt='%d',
               delimiter=',')

    ## oversample the minority samples ONLY in training data
    if args.test_or_train == 'train':
        X_train, Y_train = oversample_train(X_train, Y_train, args.num_classes)
        print("After oversampling--num of train class 0: ", len(np.where(Y_train == 0)[0]), "\n num of train class 1: ", len(np.where(Y_train == 1)[0]))

        if args.aug_folds != 0:
            train_data = augment_data(X_train, args)
            args.num_train = train_data["spectra"].shape[0]
            print("After augmentation--num of train class 0: ", len(np.where(train_data["labels"] == 0)[0]), "num of train class 1: ",
                  len(np.where(train_data["labels"] == 1)[0]))
        else:
            train_data["spectra"] = X_train[:, 3:]
            train_data["labels"] = Y_train
            true_lables = X_train[:, 2]
            train_data["ids"] = X_train[:, 1]
            train_data["sample_ids"] = X_train[:, 0]

        train_data["num_samples"] = len(Y_train)
        train_data["spectra"] = zscore(train_data["spectra"], axis=1).astype(np.float32)
        train_data["labels"] = train_data["labels"].astype(np.int32)
        # assert np.sum(train_data["labels"].astype(np.int32) == true_lables.astype(np.int32)) == len(
        #     train_data["labels"]), "train_test_split messed up the data!"
        train_data["ids"] = train_data["ids"].astype(np.int32)
        train_data["sample_ids"] = train_data["sample_ids"].astype(np.int32)

        train_count = dict(Counter(list(train_data["ids"])))  # count the num of samples of each id
        sorted_count = sorted(train_count.items(), key=lambda kv: kv[1])
        np.savetxt(os.path.join(args.output_path, "train_ids_count.csv"), np.array(sorted_count), fmt='%d', delimiter=',')

    return train_data, test_data


def get_data_from_certain_ids(args, certain_fns=["f1", "f2"]):
    """
    Load data from previous certain examples
    :param args:
    :param certain_fns: list of filenames, from train and validation
    :return:
    """
    mat = scipy.io.loadmat(args.input_data)["DATA"]
    labels = mat[:, 1]

    new_mat = np.zeros((mat.shape[0], mat.shape[1] + 1))
    new_mat[:, 0] = np.arange(mat.shape[0])   # tag every sample
    new_mat[:, 1:] = mat
    train_data = {}
    test_data = {}

    certain_mat = np.empty((0, new_mat.shape[1]))
    for fn in certain_fns:
        certain = pd.read_csv(fn, header=0).values
        certain_inds = certain[:, 0].astype(np.int)
        certain_mat = np.vstack((certain_mat, new_mat[certain_inds]))
        print(os.path.basename(fn), len(certain_inds), "samples\n")

    print("certain samples 0: ", len(np.where(certain_mat[:, 2] == 0)[0]), "\ncertain samples 1: ", len(np.where(certain_mat[:, 2] == 1)[0]))

    if args.test_or_train == 'train':
        temp_rand = np.arange(len(certain_mat))
        np.random.shuffle(temp_rand)
        mat_shuffle = certain_mat[temp_rand]
    elif args.test_or_train == 'test':   # In test, don't shuffle
        mat_shuffle = certain_mat
        print("data labels: ", mat_shuffle[:, 2])

    X_train, X_test, Y_train, Y_test = train_test_split(mat_shuffle, mat_shuffle[:, 2], test_size=args.test_ratio/100.)

    test_data["spectra"] = zscore(X_test[:, 3:], axis=1).astype(np.float32)
    test_data["labels"] = Y_test.astype(np.int32)
    test_data["ids"] = X_test[:, 1].astype(np.int32)
    test_data["sample_ids"] = X_test[:, 0].astype(np.int32)
    test_data["num_samples"] = len(test_data["labels"])
    assert np.sum(Y_test.astype(np.int32) == X_test[:, 2].astype(np.int32)) == len(
        X_test), "train_test_split messed up the data!"
    print("Test num of class 0: ", len(np.where(test_data["labels"] == 0)[0]), "num of class 1: ", len(np.where(test_data["labels"] == 1)[0]))
    #
    test_count = dict(Counter(list(test_data["ids"])))  # count the num of samples of each id
    sorted_count = sorted(test_count.items(), key=lambda kv: kv[1])
    np.savetxt(os.path.join(args.output_path, "test_ids_count.csv"), np.array(sorted_count), fmt='%d',
               delimiter=',')
    np.savetxt(os.path.join(args.output_path, "original_labels.csv"), np.array(test_data["labels"]), fmt='%d',
               delimiter=',')

    ## oversample the minority samples ONLY in training data
    if args.test_or_train == 'train':
        X_train, Y_train = oversample_train(X_train, Y_train, args.num_classes)
        print("Train After oversampling--class 0: ", len(np.where(Y_train == 0)[0]), "class 1: ",
              len(np.where(Y_train == 1)[0]))
        # augment the training data
        if args.aug_folds != 0:
            train_data = augment_data(X_train, args)
            args.num_train = train_data["spectra"].shape[0]
            print("Train After augmentation--class 0: ", len(np.where(train_data["labels"] == 0)[0]), "class 1: ", len(np.where(train_data["labels"] == 1)[0]))
        else:
            train_data["spectra"] = X_train[:, 3:]
            train_data["labels"] = Y_train
            true_lables = X_train[:, 2]
            train_data["ids"] = X_train[:, 1]
            train_data["sample_ids"] = X_train[:, 0]

        train_data["num_samples"] = len(train_data["labels"])
        train_data["spectra"] = zscore(train_data["spectra"], axis=1).astype(np.float32)
        train_data["labels"] = train_data["labels"].astype(np.int32)
        # assert np.sum(train_data["labels"].astype(np.int32) == true_lables.astype(np.int32)) == len(
        #     train_data["labels"]), "train_test_split messed up the data!"
        train_data["ids"] = train_data["ids"].astype(np.int32)
        train_data["sample_ids"] = train_data["sample_ids"].astype(np.int32)

        args.num_train = train_data["spectra"].shape[0]

        train_count = dict(Counter(list(train_data["ids"])))  # count the num of samples of each id
        sorted_count = sorted(train_count.items(), key=lambda kv: kv[1])
        np.savetxt(os.path.join(args.output_path, "train_ids_count.csv"), np.array(sorted_count), fmt='%d', delimiter=',')

    return train_data, test_data


def oversample_train(features, labels, num_classes):
    """
    Oversample the minority samples
    :param train_data:"spectra", 2d array, "labels", 1d array
    :return:
    """
    from imblearn.over_sampling import RandomOverSampler
    ros = RandomOverSampler(random_state=34)
    X_resampled, y_resampled = ros.fit_resample(features, labels)
    
    return X_resampled, y_resampled
    

def augment_data(X_train, args):
    """
    Get the augmentation based on mean of subset. ONly do it on train spectra

    :param X_train: 2d array, n_sample * 291 [sample_id, patient_id, label, features*288]
    :param args
    :return: train_aug: dict
    """
    train_data_aug = {}
    X_train_aug = X_train

    if "mean" in args.aug_method:
        X_train_aug =  augment_with_batch_mean(args, X_train, X_train_aug)
    if "both" == args.aug_method:
        X_train_aug =  augment_with_batch_mean(args, X_train, X_train_aug)
    elif args.aug_method == "noise":
        X_train_aug =  augment_with_random_noise(args, X_train, X_train_aug)
    #
    # print("Augmentation number of class 0", np.where(X_train_aug[:, 2] == 0)[0].size, "number of class 1", np.where(X_train_aug[:, 2] == 1)[0].size)
    train_data_aug["spectra"] = X_train_aug[:, 3:].astype(np.float32)
    train_data_aug["labels"] = X_train_aug[:, 2].astype(np.int32)
    train_data_aug["ids"] = X_train_aug[:, 1].astype(np.int32)
    train_data_aug["sample_ids"] = X_train_aug[:, 0].astype(np.int32)

    return train_data_aug


def augment_with_batch_mean(args, X_train, X_train_aug):
    """
    Augment the original spectra with the mini-mini-same-class-batch mean
    :param X_train: 2d array  [sample_id, patient_id, label, features*288]
    :param train_data_aug: 2d array
    :return:
    train_data_aug: 2d array
    """
    num2average = 1
    for class_id in range(args.num_classes):
        # find all the samples from this class
        if args.aug_method == "ops_mean":
            inds = np.where(X_train[:, 2] == args.num_classes - 1 - class_id)[0]
        elif args.aug_method == "same_mean":
            inds = np.where(X_train[:, 2] == class_id)[0]
        elif args.aug_method == "both_mean":
            inds = np.arange(len(X_train[:, 2]))   # use all labels to augment

        # randomly select 100 groups of 100 samples each and get mean
        aug_inds = np.random.choice(inds, inds.size*num2average, replace=True).reshape(-1, num2average)  # random pick 10000 samples and take mean every num2average samples
        mean_batch = np.mean(X_train[:, 3:][aug_inds], axis=1)   # get a batch of spectra to get the mean
        # get zscore of the mean_batch. Out of scale! NOt a good idea
        # mean_batch = (mean_batch - np.mean(mean_batch, axis=1)[:, np.newaxis]) / np.std(mean_batch, axis=1)[:, np.newaxis]

        plot_aug_examples(mean_batch, num2average, X_train[:, 3:], X_train[:, 2], args)

        for fold in range(args.aug_folds):
            aug_zspec = (1 - args.aug_scale) * X_train[:, 3:][inds] + mean_batch[np.random.choice(mean_batch.shape[0], inds.size)] * args.aug_scale
            combine = np.concatenate((X_train[:, 0][inds].reshape(-1, 1), X_train[:, 1][inds].reshape(-1, 1), X_train[:, 2][inds].reshape(-1, 1), aug_zspec), axis=1)
            X_train_aug = np.vstack((X_train_aug, combine))

    print("original spec total shape", class_id, X_train[:, 3:].shape, "augment spec shape: ", X_train_aug[:, 3:].shape)
    return X_train_aug


def augment_with_random_noise(args, X_train, train_aug):
    """
    Add random noise on the original spectra
    :param X_train: dict
    :param train_aug: dict
    :return: train_data_aug: dict
    """
    noise = args.aug_scale * \
            np.random.uniform(size=[args.aug_folds, X_train[:, 2].size, X_train[:, 3:].shape[-1]])

    for fold in range(args.aug_folds):
        aug_zspec = X_train[:, 3:] + noise[fold]
        combine = np.concatenate((X_train[:, 0][inds].reshape(-1, 1),
                                  X_train[:, 1][inds].reshape(-1, 1),
                                  X_train[:, 2][inds].reshape(-1, 1),
                                  aug_zspec))
        train_aug = np.vstack((train_aug, combine))

    return train_aug



def get_data_tensors(args, certain_fns=None):
    """
    Get batches of data in tf.dataset
    :param args:
    :param certain_fns:
    :return:
    """
    data = {}
    if not certain_fns:
        train_data, test_data = get_data(args)
    else:
        train_data, test_data = get_data_from_certain_ids(args, certain_fns=certain_fns)
    
    test_spectra, test_labels, test_ids, test_sample_ids = tf.constant(test_data["spectra"]), tf.constant(test_data["labels"]), tf.constant(test_data["ids"]), tf.constant(test_data["sample_ids"])
    test_ds = tf.data.Dataset.from_tensor_slices((test_spectra, test_labels, test_ids, test_sample_ids)).batch(args.test_bs)
    if test_data["num_samples"] < args.test_bs:
        args.test_bs = test_data["num_samples"]
    
    iter_test = tf.compat.v1.data.make_initializable_iterator(test_ds)
    data["test_initializer"] = iter_test.initializer
    batch_test = iter_test.get_next()
    data["test_features"] = batch_test[0]
    data["test_labels"] = tf.one_hot(batch_test[1], args.num_classes)
    data["test_ids"] = batch_test[2]
    data["test_sample_ids"] = batch_test[3]
    data["test_num_samples"] = test_data["num_samples"]
    data["test_batches"] = test_data["num_samples"] // args.test_bs
    print("test samples: ", test_data["num_samples"], "num_batches: ", data["test_batches"])
    if args.test_or_train == 'train':
        train_spectra, train_labels, train_sample_ids = tf.constant(train_data["spectra"]), tf.constant(train_data["labels"]), tf.constant(train_data["sample_ids"])
        train_ds = tf.data.Dataset.from_tensor_slices((train_spectra, train_labels, train_sample_ids)).shuffle(buffer_size=8000).repeat().batch(
            args.batch_size)
        iter_train = train_ds.make_initializable_iterator()
        batch_train = iter_train.get_next()
        data["train_features"] = batch_train[0]
        data["train_labels"] = tf.one_hot(batch_train[1], args.num_classes)
        data["train_sample_ids"] = batch_train[2]  # in training, we don't consider patient-ids
        data["train_initializer"] = iter_train.initializer
        data["train_num_samples"] = train_data["num_samples"]
        data["train_batches"] = train_data["num_samples"] // args.batch_size
        args.test_every = train_data["num_samples"] // (args.test_freq * args.batch_size)
        # test_freq: how many times to test in one training epoch

    return data, args


## Make the output dir
# @param args the arguments passed to the software
def make_output_dir(args, sub_folders=["CAMs"]):
    if os.path.isdir(args.output_path):
        logger.critical("Output path already exists. Please use an other path.")
        raise FileExistsError("Output path already exists.")
    else:
        os.makedirs(args.output_path)
        os.makedirs(args.model_save_dir)
        for sub in sub_folders:
            os.makedirs(os.path.join(args.output_path, sub))
        # copy and save all the files
        copy_save_all_files(args)
        print(args.input_data)
        print(args.output_path)



def save_command_line(args):
    cmd = " ".join(sys.argv[:])
    with open(args.output_path + "/command_line.txt", 'w') as f:
        f.write(cmd)


def save_plots(sess, args, output_data, training=False, epoch=0):
    logger.info("Saving output data")
    plot.all_figures(sess, args, output_data, training=training, epoch=epoch)
    logger.info("Output data saved to {}".format("TODO"))


def load_model(saver, sess, save_dir):
    ckpt = tf.train.get_checkpoint_state(save_dir)
    if ckpt:
        logger.info('Checkpoint found: {}'.format(ckpt.model_checkpoint_path))
        global_step = int(ckpt.model_checkpoint_path
                          .split('/')[-1]
                          .split('-')[-1])
        logger.info('  Global step was: {}'.format(global_step))
        logger.info('  Restoring...')
        saver.restore(sess, ckpt.model_checkpoint_path)
        logger.info(' Done.')
        return global_step
    else:
        logger.info(' No checkpoint found.')
        return None


def save_my_model(saver, sess, save_dir, step, name=None):
    """
    Save the model under current step into save_dir
    :param saver: tf.Saver
    :param sess: tf.Session
    :param save_dir: str, directory to save the model
    :param step: int, current training step
    :param name: if specify a name, then save with this name
    :return:
    """
    model_name = 'model.ckpt'
    if not name:
        checkpoint_path = os.path.join(save_dir, model_name)
    else:
        checkpoint_path = os.path.join(save_dir, name + model_name)
    logger.info('Saving checkpoint to {} ...'.format(save_dir))
    sys.stdout.flush()

    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    saver.save(sess, checkpoint_path, global_step=step)
    logger.info('Done.')


def copy_save_all_files(args):
    """
    Copy and save all files related to model directory
    :param args:
    :return:
    """
    src_dir = '../src'
    save_dir = os.path.join(args.model_save_dir, 'src')
    if not os.path.exists(save_dir):  # if subfolder doesn't exist, should make the directory and then save file.
        os.makedirs(save_dir)
    req_extentions = ['py', 'json']
    for filename in os.listdir(src_dir):
        exten = filename.split('.')[-1]
        if exten in req_extentions:
            src_file_name = os.path.join(src_dir, filename)
            target_file_name = os.path.join(save_dir, filename)
            with open(src_file_name, 'r') as file_src:
                with open(target_file_name, 'w') as file_dst:
                    for line in file_src:
                        file_dst.write(line)
    print('Done WithCopy File!')


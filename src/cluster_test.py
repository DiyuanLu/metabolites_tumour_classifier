import time
import os
import numpy as np
import logging
default_aug_method = "ops_mean"
default_factor = 0.2
default_folds = 5
default_aug_scale = 0.3
default_from_epoch = 3
default_input_data = "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_train_test_data5.mat"
EXPERIMENT_DIR_ROOT = "/home/epilepsy-data/data/metabolites/results"


def generate_experiment_path_str(description=None, restore_from=None, input_data=None):
    if restore_from:
        restore_from = restore_from
    else:
        raise ValueError('A model dir should be passed into!')
    description = description if description else "test"
    cv_set_id = os.path.basename(input_data).split("_")[-1].split(".")[0]
    experiment_dir = os.path.dirname(restore_from) + "_on_{}_{}".format(cv_set_id, description)
    return experiment_dir


def make_output_dir(output_path, sub_folders=["CAMs"]):
    if os.path.isdir(output_path):
        logging.critical("Output path already exists. Please use an other path.")
        raise FileExistsError("Output path already exists.")
    else:
        os.makedirs(output_path)
        model_save_dir = os.path.join(output_path, "network")
        os.makedirs(model_save_dir)
        for sub in sub_folders:
            os.makedirs(os.path.join(output_path, sub))
        # copy and save all the files
        copy_save_all_files(model_save_dir)


def copy_save_all_files(model_save_dir):
    """
    Copy and save all files related to model directory
    :param model_save_dir:
    :return:
    """
    src_dir = '../src'
    save_dir = os.path.join(model_save_dir, 'src')
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


class ClusterQueue:
    def __init__(self, **kwargs):
        # generate a path for the results + mkdir
        # TODO
        self.output_path = generate_experiment_path_str(
            description=kwargs["description"] if "description" in kwargs else None,
            restore_from=kwargs["restore_from"] if "restore_from" in kwargs else None,
            input_data=kwargs["input_data"] if "input_data" in kwargs else default_input_data,
        )
        make_output_dir(self.output_path, sub_folders=["AUCs", "CAMs", 'CAMs/mean', "wrong_examples", "certains"])

        # output path for the experiment log
        self.cmd_slurm = "sbatch --output {}/%N_%j.log".format(self.output_path)

        # special treatment for the "description" param (for convevience)
        if "description" in kwargs:
            self.cmd_slurm += " --job-name {}".format(kwargs["description"])
        self.cmd_slurm += " cluster_test.sh"

        # Creating the flags to be passed to classifier.py
        self.cmd_python = ""
        for k, v in kwargs.items():
            # _key_to_flag transforms "something_stupid"   into   "--something-stupid"
            flag = self._key_to_flag(k)
            # _to_arg transforms ("--something-stupid", a_value)   into   "--something-stupid a_value"
            arg = self._to_arg(flag, v)
            self.cmd_python += arg
        self.cmd_python += self._to_arg("--output_path", self.output_path)

        self.cmd = self.cmd_slurm + self.cmd_python
        print("#########################################################")
        print(self.cmd_slurm, "\n")
        print(self.cmd_python)
        print("##########################################################\n")
        # TODO
        os.system(self.cmd)

        time.sleep(1)

    def _key_to_flag(self, key):
        return "--" + key.replace("_", "_")

    def _to_arg(self, flag, v):
        return " {} {}".format(flag, v)

    def watch_tail(self):
        os.system("watch tail -n 40 \"{}\"".format(self.output_path + "/log/*.log"))


model_dirs = [
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-50_noisex2_factor_0.02_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-51_noisex5_factor_0.02_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-52_noisex7_factor_0.02_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-53_noisex10_factor_0.02_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-54_noisex2_factor_0.06_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-56_noisex5_factor_0.06_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-57_noisex7_factor_0.06_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-58_noisex10_factor_0.06_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-26-59_noisex2_factor_0.08_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-00_noisex5_factor_0.08_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-01_noisex7_factor_0.08_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-03_noisex10_factor_0.08_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-04_noisex2_factor_0.1_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-05_noisex5_factor_0.1_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-06_noisex7_factor_0.1_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-07_noisex10_factor_0.1_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-08_noisex2_factor_0.12_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-10_noisex5_factor_0.12_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-11_noisex7_factor_0.12_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-12_noisex10_factor_0.12_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-13_noisex2_factor_0.14_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-14_noisex5_factor_0.14_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-15_noisex7_factor_0.14_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-17_noisex10_factor_0.14_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-18_noisex2_factor_0.16_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-19_noisex5_factor_0.16_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-20_noisex7_factor_0.16_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-21_noisex10_factor_0.16_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-22_noisex2_factor_0.18_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-24_noisex5_factor_0.18_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-25_noisex7_factor_0.18_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-26_noisex10_factor_0.18_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-27_noisex2_factor_0.2_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-28_noisex5_factor_0.2_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-29_noisex7_factor_0.2_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-31_noisex10_factor_0.2_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-32_noisex2_factor_0.3_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-33_noisex5_factor_0.3_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-34_noisex7_factor_0.3_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-35_noisex10_factor_0.3_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-36_noisex2_factor_0.4_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-38_noisex5_factor_0.4_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-39_noisex7_factor_0.4_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-40_noisex10_factor_0.4_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-41_noisex2_factor_0.5_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-42_noisex5_factor_0.5_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-43_noisex7_factor_0.5_from-epoch_99_from-lout40_data5_train/network",
"/home/epilepsy-data/data/metabolites/results/2020-04-23T20-27-45_noisex10_factor_0.5_from-epoch_99_from-lout40_data5_train/network",
]
source = [
    "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data5.mat"]
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data0.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data1.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data2.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data3.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data4.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data6.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data7.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data8.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data9.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data5.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data0.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data1.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data2.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data3.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data4.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data6.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data7.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data8.mat",
    # "/home/elu/LU/2_Neural_Network/2_NN_projects_codes/Epilepsy/metabolites_tumour_classifier/data/20190325/20190325-3class_lout40_val_data9.mat" ]

for model, test_data in zip(model_dirs, source*len(model_dirs)):
    cq = ClusterQueue(restore_from=model, input_data=test_data)
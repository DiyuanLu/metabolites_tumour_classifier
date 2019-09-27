## @package graph
#  Package responsible for the tensorflow graph definition.
#
#  This package provides functions to define a multi-layer perceptron according to the arguments passed.
#  It also provides separate functions to define the loss and the training algorithm.
import tensorflow as tf
import numpy as np
import logging as log
import ipdb
logger = log.getLogger("classifier")

regularizer = tf.keras.regularizers.l2(l=0.01)
# python3
initializer = tf.keras.initializers.he_normal(seed=589)
# initializer = tf.compat.v1.initializers.he_normal()

def convert_activation(acti_names):
    acti_funcs = []
    for act in acti_names:
        if act == 'relu':
            acti_funcs.append(tf.nn.relu)
        elif act == 'lrelu':
            acti_funcs.append(tf.nn.leaky_relu)
        elif act == 'tanh':
            acti_funcs.append(tf.tanh)
        elif act == 'sigmoid':
            acti_funcs.append(tf.nn.sigmoid)
        elif act == 'softmax':
            acti_funcs.append(tf.nn.softmax)
        elif act == 'None':
            acti_funcs.append(None)
        else:
            raise NameError("Activation function not recognized: {}".format(act))
    return acti_funcs


## Class for a Multilayer perceptron
# defines and store the layers of the network
# implements batch normalization and dropout
class MLP:
    ## Constructor
    #  @param args arguments passed to the command line
    def __init__(self, args):
        logger.debug("Defining multilayer perceptron")
        self.layer_dims = np.array(args.layer_dims)
        self.batch_norms = np.array(args.batch_norms)
        self.activations = convert_activation(args.activations)
        self.dropout_probs = np.array(args.dropout_probs)
        assert(self.layer_dims[-1] == args.num_classes), "Softmax output does not match number of classes"
        assert(self.layer_dims[0] == args.data_len), "Dim of first layer should be the same as the data length"
        assert(len(self.batch_norms) ==
               len(self.activations) ==
               len(self.dropout_probs) ==
               len(self.layer_dims) - 1), "Passed in dims of batch norms or activations or drop do not match"
        self.n_layers = len(self.batch_norms)
        self._net_constructed_once = False
        self._define_variables()

    def _define_variables(self):
        self.weights = []
        self.biases = []
        initializer = tf.contrib.layers.xavier_initializer()
        for in_size, out_size, batch_norm in zip(self.layer_dims[0:-1], self.layer_dims[1:], self.batch_norms):
            # random = tf.truncated_normal(stddev=0.01, shape=(in_size, out_size))
            W = tf.Variable(initializer((in_size, out_size)), dtype=tf.float32)
            B = None if batch_norm else tf.Variable(tf.zeros(shape=(1, out_size)))
            self.weights.append(W)
            self.biases.append(B)

    def __call__(self, features, training=False):
        out = {}
        net = features
        for i in range(self.n_layers - 1):
            net = self._make_layer(net, i, training)
        activity = net
        net = self._make_layer(net, i+1, training)
        out["logits"] = net
        self._net_constructed_once = True
        return out

    ## Private function for adding layers to the network
    # @param inp input tensor
    # @param out_size size of the new layer
    # @param batch_norm bool stating if batch normalization should be used
    # @param dropout droupout probability. Set to 0 to disable
    # @param activation activation function
    def _make_layer(self, inp, layer_number, training):
        out_size = self.layer_dims[layer_number + 1]
        batch_norm = self.batch_norms[layer_number]
        dropout = self.dropout_probs[layer_number]
        activation = self.activations[layer_number]
        _to_format = [out_size, batch_norm, dropout, activation, training]
        layer_name = "layer_{}".format(layer_number + 1)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\tActivation = {} (training = {})"
        logger.debug(string.format(*_to_format))

        # W = self.weights[layer_number]
        # B = self.biases[layer_number]
        print("-------Building network-----------")
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            net = tf.layers.dense(inp, out_size,
                                  kernel_initializer=initializer,
                                  activation=activation)
            # net = tf.matmul(tf.squeeze(inp), W) if B is None else tf.matmul(tf.squeeze(inp), W) + B
            net = tf.layers.batch_normalization(net, training=training) if batch_norm else net
            # net = net if activation is None else activation(net)
            net = tf.layers.dropout(net, rate=dropout, training=training) if dropout != 0 else net
            print("layer: {}, in_size:{}, out_size:{}".format(layer_name, inp.get_shape().as_list(), net.get_shape().as_list()))
            return net


class CNN:
    ## Constructor
    # construct a CNN: cnn 8*3*1-pool2*1-cnn 16*3*1-pool2*1-cnn 32 3*1-pool2*1-fnn--softmax(class)
    #  @param args arguments passed to the command line
    def __init__(self, args):
        logger.debug("Defining CNN")
        self.data_len = args.data_len
        self.out_channels = np.array(args.out_channels)
        self.fc_dims = np.array(args.fc)
        self.kernel_size = args.kernel_size
        self.pool_size = args.pool_size
        self.bn_cnn = np.array(args.batch_norms)[0:len(self.out_channels)]
        self.bn_fnn= np.array(args.batch_norms)[len(self.out_channels):]
        self.activations_cnn = convert_activation(args.activations)[0:len(self.out_channels)]
        self.activations_fnn = convert_activation(args.activations)[len(self.out_channels):]
        self.drop_cnn = np.array(args.dropout_probs)[0:len(self.out_channels)]
        self.drop_fnn = np.array(args.dropout_probs)[len(self.out_channels):]
        
        assert(self.fc_dims[-1] == args.num_classes), "Softmax output does not match number of classes"
        assert (len(self.bn_cnn) == len(self.out_channels) == len(self.drop_cnn) == len(self.activations_cnn))
        assert (len(self.bn_fnn) == len(self.fc_dims) == len(self.drop_fnn) == len(self.activations_fnn))

    def __call__(self, features, training=False):
        out = {}
        net = tf.reshape(features, [-1, self.data_len, 1])
        self._net_constructed_once = True
        net = self.construct_cnn_layers(out, training)
        net = self.construct_fnn_layers(out, training)
        out["logits"] = net
        return out

    def construct_cnn_layers(self, inp, training):
        """
        Construct the whole cnn layers
        :param inp:
        :param training:
        :return:
        """
        layer_number = 1
        net = inp
        for (out_ch, bn, activation, drop) in zip(self.out_channels, self.bn_cnn, self.activations_cnn, self.drop_cnn):
            net = self._make_cnn_layer(net, out_ch, bn, activation, drop, layer_number, training)
            layer_number += 1

        return net

    def construct_fnn_layers(self, inp, training):
        """
        Construct the whole fully-connected layers
        :param inp: input tensors
        :param training: bool
        :return: output tensors of the layers
        """
        layer_number = 1
        net = tf.layers.flatten(inp)
        for (out_dim, bn, activation, drop) in zip(self.fc_dims, self.bn_cnn, self.activations_cnn, self.drop_cnn):
            net = self._make_fnn_layer(net, out_dim, bn, activation, drop, layer_number, training)
            layer_number += 1

        return net

    ## Private function for adding one conv layers to the network
    # @param inp input tensor
    # @param out_ch size of the new layer
    # @param pool, kernel size of the pooling layer
    # @param out_ch size of the new layer
    # @param bn bool stating if batch normalization should be used
    # @param activation activation function
    # @param drop, float droupout probability. Set to 0 to disable
    # @param layer_number, int droupout probability. Set to 0 to disable
    # @param training, bool
    def _make_cnn_layer(self, inp, out_ch, bn, activation, drop, layer_number, training):
        _to_format = [out_ch, bn, drop, activation, training]
        layer_name = "cnn_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\tActivation = {} (training = {})"
        logger.debug(string.format(*_to_format))
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_ch))
            kernel_size = inp.get_shape().as_list()[1]
            out = tf.layers.conv1d(inp, out_ch,
                                   kernel_size, 1,
                                   padding='SAME',
                                   kernel_initializer=initializer)
            out = tf.layers.max_pooling1d(out, self.pool_size, self.pool_size, padding="SAME")
            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = out if activation is None else activation(out)
            out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))
        
        return out

    ## Private function for adding fully-connected layers to the network
    # @param inp input tensor
    # @param out_size size of the new layer
    # @param batch_norm bool stating if batch normalization should be used
    # @param dropout droupout probability. Set to 0 to disable
    # @param activation activation function
    def _make_fnn_layer(self, inp, out_dim, bn, activation, drop, layer_number, training):
        _to_format = [out_dim, bn, drop, activation, training]
        layer_name = "fc_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\tActivation = {} (training = {})"
        logger.debug(string.format(*_to_format))
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_dim))
            out = tf.layers.dense(inp, out_dim,
                                  kernel_initializer=initializer,
                                  activation=activation)
            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))
        return out


class CNN_CAM:
    ## Constructor
    # construct a CNN: cnn 8*3*1-pool2*1-cnn 16*3*1-pool2*1-cnn 32 3*1-pool2*1-fnn--softmax(class)
    #  @param args arguments passed to the command line
    def __init__(self, args):
        logger.debug("Defining CNN")
        self.data_len = args.data_len
        self.out_channels = np.array(args.out_channels)
        self.kernel_size = args.kernel_size
        self.pool_size = args.pool_size
        self.strides = args.strides
        self.bn_cnn = np.array(args.batch_norms)[0:len(self.out_channels)]
        self.activations_cnn = convert_activation(args.activations)[0:len(self.out_channels)]
        self.drop_cnn = np.array(args.dropout_probs)[0:len(self.out_channels)]
        self.num_classes = args.num_classes
        self.num_layers = args.num_layers

        assert (len(self.bn_cnn) == len(self.out_channels) == len(self.drop_cnn) == len(self.activations_cnn))
    
    def __call__(self, features, training=False):
        out = {}
        inp = tf.reshape(features, [-1, self.data_len, 1])
        self._net_constructed_once = True
        out["conv"] = self.construct_cnn_layers(inp, training)
        # GAP layer - global average pooling
        with tf.variable_scope('GAP', reuse=tf.AUTO_REUSE) as scope:
            net_gap = tf.reduce_mean(out["conv"], (1))  # get the mean of axis 1 and 2 resulting in shape [batch_size, filters]
            print("gap shape", net_gap.shape.as_list())
    
            gap_w = tf.get_variable('W_gap', shape=[net_gap.get_shape().as_list()[-1], self.num_classes], initializer=tf.random_normal_initializer(0., 0.01))
            logits = tf.nn.softmax(tf.matmul(net_gap, gap_w))
            
        out["logits"] = logits
        out["gap_w"] = gap_w
        return out
    
    def construct_cnn_layers(self, inp, training):
        """
        Construct the whole cnn layers
        :param inp:
        :param training:
        :return:
        """
        layer_number = 1
        out = inp
        for (out_ch, bn, activation, drop, num_l) in zip(self.out_channels, self.bn_cnn, self.activations_cnn, self.drop_cnn, self.num_layers):
            out = self._make_cnn_layer(out, out_ch, bn, activation, drop, layer_number, num_l, training)
            layer_number += 1
        
        return out
    
    def construct_fnn_layers(self, inp, training):
        """
        Construct the whole fully-connected layers
        :param inp: input tensors
        :param training: bool
        :return: output tensors of the layers
        """
        layer_number = 1
        out = tf.layers.flatten(inp)
        for (out_dim, bn, activation, drop) in zip(self.fc_dims, self.bn_cnn, self.activations_cnn, self.drop_cnn):
            out = self._make_fnn_layer(out, out_dim, bn, activation, drop, layer_number, training)
            layer_number += 1
        
        return out
    

    def _make_cnn_layer(self, inp, out_ch, bn, activation, drop, layer_number, num_layers, training):
        """
        To creat CNN block
        :param inp:
        :param out_ch: int, num of filters to use
        :param bn: bool
        :param activation: tf function
        :param drop: float, drop rate
        :param layer_number: int
        :param num_layers: int, how many layers in one CNN block, like VGG
        :param training:
        :return:
        """
        _to_format = [out_ch, bn, drop, activation, training]
        layer_name = "cnn_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\tActivation = {} (training = {})"
        logger.debug(string.format(*_to_format))
        out = inp
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_ch))
            if self.kernel_size >= 100:
                kernel_size = inp.get_shape().as_list()[1] // 2  # later layers, the filter size should be adjusted by the input
            else:
                kernel_size = self.kernel_size
            out = tf.layers.conv1d(out, out_ch,
                                   kernel_size, 1,
                                   kernel_initializer=initializer,
                                   padding='SAME')
            # if np.mod(layer_number, 2) == 1:  # only pool after odd number layer
            #     out = tf.layers.max_pooling1d(out, self.pool_size, self.strides, padding="SAME")
            out = tf.layers.max_pooling1d(out, self.pool_size, self.pool_size, padding="SAME")
            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = out if activation is None else activation(out)
            out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))
        
        return out
    
    ## Private function for adding fully-connected layers to the network
    # @param inp input tensor
    # @param out_size size of the new layer
    # @param batch_norm bool stating if batch normalization should be used
    # @param dropout droupout probability. Set to 0 to disable
    # @param activation activation function
    def _make_fnn_layer(self, inp, out_dim, bn, activation, drop, layer_number, training):
        _to_format = [out_dim, bn, drop, activation, training]
        layer_name = "fc_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\tActivation = {} (training = {})"
        logger.debug(string.format(*_to_format))
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_dim))
            out = tf.layers.dense(inp, out_dim,
                                  kernel_initializer=initializer,
                                  activation=activation)
            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))
        return out


class Res_ECG_CAM:
    ## Constructor
    # construct a CNN: cnn 8*3*1-pool2*1-cnn 16*3*1-pool2*1-cnn 32 3*1-pool2*1-fnn--softmax(class)
    #  @param args arguments passed to the command line
    def __init__(self, args):
        logger.debug("Defining Res_ECG")
        self.data_len = args.data_len
        self.channel_start = args.out_channels  # Starting num of channels
        self.num_layers_in_res = args.num_layers_in_res  #
        self.num_res_blocks = args.num_res_blocks
        self.kernel_size = args.filter_size  # repeat for all the cnn
        self.pool_size = args.pool_size  # repeat for all the cnn
        self.stride = args.stride  # repeat for all the cnn
        self.drop_cnn = args.drop_cnn  # repeat for all the cnn
        self.bn = args.bn
        self.num_classes = args.num_classes
        self.increase_interval = min(self.num_res_blocks // 3, 4)

    def __call__(self, features, training=False):
        ret = {}
        if len(features.get_shape().as_list()) < 3:
            inp = tf.reshape(features, [-1, self.data_len, 1, 1])
        else:
            inp = tf.expand_dims(features, axis=3)
        self._net_constructed_once = True

        out = self._make_cnn_layer(inp, self.channel_start,
                                   self.bn, self.drop_cnn, 1, 1,
                                   training=training)
        out = self.build_res_block_ecg_1st(out, training=training)

        ret["conv"] = self.construct_res_blocks_ecg(out, training=training)
        # GAP layer - global average pooling
        with tf.variable_scope('GAP', reuse=tf.AUTO_REUSE) as scope:
            net_gap = tf.squeeze(tf.reduce_mean(ret["conv"], (1)), axis=1) # get the mean of axis 1 and 2 resulting in shape [batch_size, filters]

            print("gap shape", net_gap.get_shape().as_list())

            gap_w = tf.get_variable('W_gap', shape=[net_gap.get_shape().as_list()[-1], self.num_classes],
                                    initializer=tf.random_normal_initializer(0., 0.01))
            logits = tf.nn.softmax(tf.matmul(net_gap, gap_w))

        ret["logits"] = logits
        ret["gap_w"] = gap_w
        return ret

    def construct_res_blocks_ecg(self, inp, training=True):
        """
        Construct the whole cnn layers
        :param inp:
        :param training:
        :return:
        """
        out = inp
        channel = self.channel_start
        k = 0
        strides = [2 if (i+1) % self.increase_interval == 0 else 1 for i in range(self.num_res_blocks)]   # downsizing in every 4 blocks
        block_ids = np.arange(self.num_res_blocks)

        for bl_id, s in zip(block_ids, strides):
            if (bl_id + 1) % self.increase_interval == 0 and bl_id > 0:
                k += 1
                channel = self.channel_start * np.power(2, k)

            out = self.build_res_blocks_ecg(out, channel, s,
                                            layer_id=bl_id, training=training)
        return out

    def _make_cnn_layer(self, inp, out_ch, bn, drop, layer_number, num_layers, training=True):
        """
        To creat CNN block
        :param inp:
        :param out_ch: int, num of filters to use
        :param bn: bool
        :param activation: tf function
        :param drop: float, drop rate
        :param layer_number: int
        :param num_layers: int, how many layers in one CNN block, like VGG
        :param training:
        :return:
        """
        _to_format = [out_ch, bn, drop, training]
        layer_name = "cnn_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\t (training = {})"
        logger.debug(string.format(*_to_format))
        out = inp
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_ch))
            kernel_size = min(self.kernel_size, inp.get_shape().as_list()[1])
            out = tf.layers.conv2d(inputs = out,
                                    filters = out_ch,
                                    kernel_size = [kernel_size, 1],
                                    strides = [1, 1],
                                    padding = 'SAME',
                                    kernel_initializer = initializer,
                                    # kernel_regularizer = regularizer,
                                    activation = None)

            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = tf.nn.relu(out)
            # out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))

        return out


    def build_res_block_ecg_1st(self, inp, training=True):
        """
        https://github.com/fchollet/deep-learning-models/blob/master/resnet50.py
        :param out_channels: int, the filters to use in this block
        :param filter_size: [height, width], the kernel size
        :param num_layers: int, how many cov layers in one resi block. inp--> (conv -->...--> conv) -->+inp-->
        :param layer_id: int, the layer id
        :return: Conv bn relu drop conv
        """
        out = inp

        with tf.variable_scope("res_block_start", reuse=tf.AUTO_REUSE):
            out = tf.layers.conv2d(
                inputs=out,
                filters=self.channel_start,
                kernel_size=[self.kernel_size, 1],
                strides=[self.stride, 1],   # reduce the height, because shortcut also reduce the height
                padding='SAME',
                kernel_initializer=initializer,
                # kernel_regularizer=regularizer,
                activation=None
            )
            out = tf.layers.batch_normalization(out, training=training)
            out = tf.nn.relu(out)
            out = tf.layers.dropout(out, self.drop_cnn, training=training)
            out = tf.layers.conv2d(
                inputs=out,
                filters=self.channel_start,
                kernel_size=[self.kernel_size, 1],
                padding='SAME',
                kernel_initializer=initializer,
                # kernel_regularizer=regularizer,
                activation=None
            )
            shortcut = tf.layers.max_pooling2d(inp, pool_size=[self.pool_size, 1],
                                               strides=[self.stride, 1],
                                               padding='same')
            output = tf.nn.relu(shortcut + out)
            print("ResiBlock_start-output pooling shape", out.shape.as_list())
            return output

    def build_res_blocks_ecg(self, x, out_channel, stride, layer_id=0, training=True):
        """
        https://github.com/fchollet/deep-learning-models/blob/master/resnet50.py
        :param out_channels: int, the filters to use in this block
        :param filter_size: [height, width], the kernel size
        :param num_layers: int, how many cov layers in one resi block. inp--> (conv -->...--> conv) -->+inp-->
        :param layer_id: int, the layer id
        :return: bn relu  conv bn relu drop conv
        """
        out = x
        if (layer_id + 1) % self.increase_interval == 0 and layer_id > 0:  # only every 4 blocks increase the number of channels and decrease the height
            zeros_x = tf.zeros_like(x)
            concat_long_ch = tf.concat([x, zeros_x], axis=3)
            x = concat_long_ch

        with tf.variable_scope("res_block" + str(layer_id), reuse=tf.AUTO_REUSE):
            for j in range(self.num_layers_in_res):  # there are two conv layers in one block
                print(training)
                out = tf.layers.batch_normalization(out, training=training)
                out = tf.nn.relu(out)
                if not (layer_id == 0 and j == 0):
                    drop = self.drop_cnn if j > 0 else 0
                    out = tf.layers.dropout(out, drop, training=training)

                out = tf.layers.conv2d(
                    inputs=out,
                    filters=out_channel,
                    kernel_size=[self.kernel_size, 1],
                    padding='SAME',
                    strides=[stride, 1] if j == 0 else [1, 1],
                    kernel_initializer=initializer,
                    # kernel_regularizer=regularizer,
                    activation=None
                )

            shortcut = tf.layers.max_pooling2d(x, pool_size=[self.pool_size, 1], strides=[stride, 1], padding='same')
            output = tf.nn.relu(shortcut + out)
            print("ResiBlock{}-output pooling shape".format(layer_id), out.shape.as_list())
            return output


class Inception_v3:
    """
    COnstructor
    Make an inception model
    """
    def __init__(self, args):
        "https://mohitjain.me/2018/06/09/googlenet/"
        logger.debug("Defining Inception model")
        self.data_len = args.data_len
        self.num_classes = args.num_classes
        self.channel_start = args.out_channels
        self.bn = self.bn
        self.activations = self.activations
        self.drop_fnn = self.drop_fnn
        self.drop_cnn = self.drop_cnn
        self.incep_fs = self.incep_filter_size
        self.filter_size = self.filter_size
        self.num_incep_blocks = self.num_incep_blocks
        self.conv_1_size = args.conv_1_size
        self.conv_3_size = args.conv_3_size
        self.conv_3_reduced_size = args.conv_3_reduced_size
        self.conv_5_reduced_size = args.conv_5_reduced_size
        self.conv_5_size = args.conv_5_size
        self.pool_size = args.pool_size
        self.stride = args.stride


    def build_inception_block(self, inp, block_id=0, training=False):
        """
        Build the inception block
        :param inp:
        :param block_id: int
        :param training: bool
        :return:
        """
        out = inp
        with tf.variable_scope("incep_{}".format(block_id), reuse=tf.AUTO_REUSE):
            out = tf.layers.conv2d(
                inputs=out,
                filters=self.channel_start,
                kernel_size=[self.kernel_size, 1],
                strides=[self.stride, 1],  # reduce the height, because shortcut also reduce the height
                padding='SAME',
                kernel_initializer=initializer,
                # kernel_regularizer=regularizer,
                activation=None
            )
            out = tf.layers.batch_normalization(out, training=training)
            out = tf.nn.relu(out)
            out = tf.layers.dropout(out, self.drop_cnn, training=training)
            out = tf.layers.conv2d(
                inputs=out,
                filters=self.channel_start,
                kernel_size=[self.kernel_size, 1],
                padding='SAME',
                kernel_initializer=initializer,
                # kernel_regularizer=regularizer,
                activation=None
            )
            shortcut = tf.layers.max_pooling2d(inp, pool_size=[self.pool_size, 1],
                                               strides=[self.stride, 1],
                                               padding='same')
            output = tf.nn.relu(shortcut + out)
            print("ResiBlock_start-output pooling shape", out.shape.as_list())
            return output


    def _make_cnn_layer(self, inp, out_ch, bn, drop, layer_number, training=True):
        """
        To creat CNN block
        :param inp:
        :param out_ch: int, num of filters to use
        :param bn: bool
        :param activation: tf function
        :param drop: float, drop rate
        :param layer_number: int
        :param training:
        :return:
        """
        _to_format = [out_ch, bn, drop, training]
        layer_name = "cnn_layer_{}".format(layer_number)
        logger.debug("Creating new layer:")
        string = "Output size = {}\tBatch norm = {}\tDropout prob = {}\t (training = {})"
        logger.debug(string.format(*_to_format))
        out = inp
        with tf.variable_scope(layer_name, reuse=tf.AUTO_REUSE):
            print("layer {} in_size {} out_size {}".format(layer_name, inp.get_shape().as_list(), out_ch))
            kernel_size = min(self.kernel_size, inp.get_shape().as_list()[1])
            out = tf.layers.conv2d(inputs = out,
                                    filters = out_ch,
                                    kernel_size = [kernel_size, 1],
                                    strides = [1, 1],
                                    padding = 'SAME',
                                    kernel_initializer = initializer,
                                    kernel_regularizer = regularizer,
                                    activation = None)

            out = tf.layers.batch_normalization(
                out, training=training) if bn else out
            out = tf.nn.relu(out)
            # out = tf.layers.dropout(out, rate=drop, training=training) if drop != 0 else out
        print("layer {} out_size {}".format(layer_name, out.get_shape().as_list()))

        return out


    def conv_layer(self, x, filter_height, filter_width,
                   num_filters, name, stride=1, padding='SAME'):

        """Create a convolution layer."""

        # Get number of input channels
        input_channels = int(x.get_shape()[-1])

        with tf.variable_scope(name) as scope:
            # Create tf variables for the weights and biases of the conv layer
            W = tf.get_variable('weights', shape=[filter_height, filter_width, input_channels, num_filters],
                                initializer=tf.random_normal_initializer(mean=0.0, stddev=0.01))

            b = tf.get_variable('biases', shape=[num_filters], initializer=tf.constant_initializer(0.0))

            # Perform convolution.
            conv = tf.nn.conv2d(x, W, strides=[1, stride, stride, 1], padding=padding)
            # Add the biases.
            z = tf.nn.bias_add(conv, b)
            # Apply ReLu non linearity.
            a = tf.nn.relu(z)

            return a


    def inception_layer(x, conv_1_size, conv_3_reduce_size,
                        conv_3_size, conv_5_reduce_size,
                        conv_5_size, pool_proj_size,
                        name='inception'):

        """ Create an Inception Layer """

        with tf.variable_scope(name) as scope:
            conv_1 = self.conv_layer(x, filter_height=1, filter_width=1,
                                num_filters=conv_1_size, name='{}_1x1'.format(name))

            conv_3_reduce = self.conv_layer(x, filter_height=1, filter_width=1,
                                       num_filters=conv_3_reduce_size, name='{}_3x3_reduce'.format(name))

            conv_3 = self.conv_layer(conv_3_reduce, filter_height=3, filter_width=3,
                                num_filters=conv_3_size, name='{}_3x3'.format(name))

            conv_5_reduce = self.conv_layer(x, filter_height=1, filter_width=1,
                                       num_filters=conv_5_reduce_size, name='{}_5x5_reduce'.format(name))

            conv_5 = self.conv_layer(conv_5_reduce, filter_height=5, filter_width=5,
                                num_filters=conv_5_size, name='{}_5x5'.format(name))

            pool =  tf.layers.max_pooling1d(x, self.pool_size, self.stride, padding="SAME")
            pool_proj = self.conv_layer(pool, filter_height=1, filter_width=1,
                                   num_filters=pool_proj_size, name='{}_pool_proj'.format(name))

            return tf.concat([conv_1, conv_3, conv_5, pool_proj], axis=3, name='{}_concat'.format(name))


    def __call__(self, features, training=False):
        ret = {}
        if len(features.get_shape().as_list()) < 3:
            inp = tf.reshape(features, [-1, self.data_len, 1, 1])
        else:
            inp = tf.expand_dims(features, axis=3)
        self._net_constructed_once = True

        out = self._make_cnn_layer(inp, self.channel_start,
                                   self.bn, self.drop_cnn,
                                   1, training = True)

        for bl in range(self.num_incep_blocks):
            out = self.build_inception_block(out, block_id=bl, training=training)

        # GAP layer - global average pooling
        with tf.variable_scope('fc', reuse=tf.AUTO_REUSE) as scope:
            flat_net = tf.layers.flatten(out) # get the mean of axis 1 and 2 resulting in shape [batch_size, filters]

            print("flatten feature map shape", flat_net.get_shape().as_list())

            logits = tf.layers.dense(flat_net, self.num_classes,
                                  kernel_initializer=initializer,
                                  activation=self.activation)

        ret["logits"] = logits

        return ret




# --------------------------utile functions-----------------------------------
## Computes the loss tensor according to the arguments passed to the software
# @param args arguments passed to the command line
# @param net the network object
# @see MLP example of a network object
def get_loss_sum(args, out, out_true):
    logger.debug("Defining loss")
    loss_type = args.loss_type
    if loss_type == "mse":
        loss = tf.reduce_sum(tf.reduce_mean((out - out_true) ** 2, axis=1))
    if loss_type == "rmse":
        loss = tf.reduce_sum(tf.reduce_mean(tf.abs(out - out_true), axis=1))
    if loss_type == "softmax_ce":
        loss = tf.reduce_sum(tf.nn.softmax_cross_entropy_with_logits(logits=out, labels=out_true))
    return loss


## Compute a tensor containing the amount of example correctly classified in a batch
# @param net the network object
# @see MLP example of a network object
def get_ncorrect(out, out_true):
    correct_prediction = tf.equal(tf.argmax(out, 1), tf.argmax(out_true, 1))
    ncorrect = tf.reduce_sum(tf.cast(correct_prediction, tf.float32))
    right_inds = correct_prediction
    # wrong_inds = tf.reshape(tf.where(tf.argmax(out, 1) != tf.argmax(out_true, 1)), [-1,])
    return ncorrect, right_inds

## Compute the confusion matrix
# @param net the network object
# @see MLP example of a network object
def get_confusion_matrix(predictions, labels, num_classes):
    conf_matrix = tf.confusion_matrix(tf.argmax(labels, 1), tf.argmax(predictions, 1), num_classes=num_classes)
    return conf_matrix


def get_roc_curve(predictions, labels, num_classes):
    """
    Get the ROC AUC curve
    :param out:
    :param out_true:
    :param num_classes:
    :return:
    """
    if num_classes == 2:
        return tf.metrics.auc(tf.argmax(labels, 1), tf.argmax(predictions, 1), curve='ROC')
    
    
## Defines an training operation according to the arguments passed to the software
# @param args arguments passed to the command line
# @param loss loss tensor
# @see get_loss_sum function to generate a loss tensor
def get_train_op(args, loss, learning_rate_op):
    logger.debug("Defining optimizer")
    optimizer_type = args.optimizer_type
    # lr = args.learning_rate
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    with tf.control_dependencies(update_ops):
        if optimizer_type == "adam":
            optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate_op).minimize(loss)
            print("learning rate", learning_rate_op)
        if optimizer_type == "rmsprop":
            optimizer = tf.train.RMSPropOptimizer(learning_rate=learning_rate_op).minimize(loss)
        if optimizer_type == "gradient_descent":
            optimizer = tf.train.GradientDescentOptimizer(learning_rate=learning_rate_op).minimize(loss)
    return optimizer


## General function defining a complete tensorflow graph
# @param args arguments passed to the command line
# @see get_loss_sum function to generate a loss tensor
# @see get_ncorrect function to generate a tensor containing number of correct classification in a batch
# @see get_optimizer function to generate an optimizer object
# @see MLP example of a network object
def get_graph(args, data_tensors):
    logger.info("Defining graph")
    graph = data_tensors
    if args.model_name == "MLP":
        net = MLP(args)
    elif args.model_name == "CNN":
        net = CNN(args)
    elif args.model_name == "CNN_CAM":
        net = CNN_CAM(args)
    elif args.model_name == "Res_ECG_CAM":
        net = Res_ECG_CAM(args)

    lr_placeholder = tf.placeholder(tf.float32, [], name='learning_rate')
    net_out = net(data_tensors["test_features"])
    graph["test_out"] = net_out["logits"]
    if "conv" in net_out.keys():
        graph["test_conv"] = net_out["conv"]
        graph["test_gap_w"] = net_out["gap_w"]
    graph["test_batch_size"] = tf.shape(graph["test_out"])[0]
    graph["test_num_batches"] = graph["test_num_samples"] // args.test_bs
    graph["test_loss_sum"] = get_loss_sum(args, graph["test_out"], data_tensors["test_labels"])
    graph["test_ncorrect"], graph["test_wrong_inds"] = get_ncorrect(graph["test_out"], data_tensors["test_labels"])
    graph["test_confusion"] = get_confusion_matrix(graph["test_out"], data_tensors["test_labels"], args.num_classes)
    graph["test_auc"] = get_roc_curve(graph["test_out"], data_tensors["test_labels"], args.num_classes)
    if args.test_or_train == "train":
        net_out = net(data_tensors["train_features"], training=True)
        graph["train_out"] = net_out["logits"]
        graph["train_labels"] = data_tensors["train_labels"]
        graph["train_batch_size"] = tf.shape(graph["train_out"])[0]
        graph["train_loss_sum"] = get_loss_sum(args, graph["train_out"], data_tensors["train_labels"])
        graph["train_ncorrect"], graph["train_wrong_inds"] = get_ncorrect(graph["train_out"], data_tensors["train_labels"])
        graph["train_confusion"] = get_confusion_matrix(graph["train_out"], data_tensors["train_labels"], args.num_classes)
        graph["learning_rate_op"] = tf.placeholder(tf.float32, [], name='learning_rate')
        # graph["train_op"] = tf.train.AdamOptimizer(learning_rate=graph["learning_rate_op"]).minimize(graph["train_loss_sum"])
        graph["train_op"] = get_train_op(args, graph["train_loss_sum"], graph["learning_rate_op"])
        

    logger.info("Graph defined")
    return graph

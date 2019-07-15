from typing import Any, Optional, Callable
import argparse
import os
from datetime import datetime

import numpy as np
import torch
from torch.utils.data import DataLoader
from torchsummary import summary
from tqdm import tqdm


from defaults import *
from data import *
from model import *
from train import *

def train(
        train: torch.utils.data.Dataset, 
        test: torch.utils.data.Dataset, 
        model: torch.nn.Module, 
        epochs: Optional[int] = EPOCHS, 
        update_freq: Optional[int] = UPDATE_FREQ,
        savepath: Optional[str] = SAVEPATH,
        save_freq: Optional[int] = SAVE_FREQ,
        batch_size: Optional[int] = BATCH_SIZE, 
        num_workers: Optional[int] = WORKERS, 
        cuda: Optional[bool] = CUDA, 
        loss_func: Optional[Callable[[float,float],None]] = None, 
        optimizer: Optional[Callable[[torch.nn.Module],torch.optim.Optimizer]]=None, 
        scheduler: Optional[Callable[[int, torch.nn.Module],None]] = None,
        silent: Optional[bool] = False
    ) -> None:
    """
    Train the provided MAPnet model.

    Note: 
    If `savepath` is specified, models will be saved in a new folder
    named according to the date and time it is run.  If mutliple instances
    are being run in parallel, each instance should have a different 
    savepath to avoid overlap.

    Furthermore, if the supplied model has been pre-trained, the naming
    scheme will not reflect this.  The user should take care to make sure
    this information is not lost.  I suggest setting savepath to the 
    datetime folder created in the previous training stage.  This way
    the model will be grouped with its 'ancestor' models.

    :param train: Dataset object containing the training data.
    :param test: Dataset object containing the test data.
    :param model: `torch.nn.Module` model to be trained.
    :param epoch: The number of epochs to train over.
    :param update_freq: Test set accuracy will be assessed every `update_freq` epochs.
    :param batch_size: batch size for training.
    :param num_workers: how many workers to use for the DataLoader.
    :param cuda: Whether to use cuda device. Defaults to False.
    :param loss_func: Loss function to use.  If `None` (default), MSELoss is used.
    :param optimizer: Optimizer to use. If `None` (default), Adam is used.
    :param scheduler: Scheduler to use. If `None` (default), no scheduler is used. 
    """

    ###########################################################################
    # Some preamble to get everything ready for training
    ###########################################################################
    train_data_loader = DataLoader(train, num_workers=num_workers,
            pin_memory=cuda, batch_size=batch_size,
            shuffle=True)

    test_data_loader = DataLoader(test, num_workers=num_workers,
            pin_memory=cuda, batch_size=batch_size,
            shuffle=True)
    desc_genr = lambda x,y,z: 'Epoch: {} Test Loss: {} Train Loss: {}'.format(
        x,
        np.format_float_scientific(y,precision=3),
        np.format_float_scientific(z,precision=3)
    )
    test_loss = 0.0

    if cuda:
        model = model.cuda().float()
    else: 
        model = model.float()

    if loss_func is None:
        loss_func = torch.nn.MSELoss()
    if optimizer is None:
        optimizer = lambda x: torch.optim.Adam(x.parameters(),lr=0.000001)

    model_optimizer = optimizer(model)
    model_scheduler = scheduler(model) if scheduler is not None else scheduler

    if savepath is not None:
        save_folder = os.path.join(savepath,datetime.now().strftime('%Y-%m-%d_%H-%M-%S'))    
        os.makedirs(save_folder)
    else:
        save_folder = None

    ###########################################################################
    # Start Training Epoch
    ###########################################################################
    for i in range(0, epochs):

        if model_scheduler is not None:
            model_scheduler.step()
        data_iterator = tqdm(train_data_loader,desc=desc_genr(i,test_loss,0),disable=silent)

        train_loss = list()
        #######################################################################
        # Cycle through each batch in the epoch 
        #######################################################################
        for index, batch in enumerate(data_iterator):
            x,label = batch
            if cuda:
                x = x.cuda()
                label = label.cuda()

            y = model(x)
            loss = loss_func(y,label.view(-1,1))
            loss_value = float(loss.item())
            train_loss.append(loss_value)
            model_optimizer.zero_grad()
            loss.backward()
            model_optimizer.step()  
            data_iterator.set_description(desc_genr(i,test_loss,np.mean(train_loss)))
    
        #######################################################################
        # Update test accuracy every `update_freq` number of epochs
        #######################################################################
        if (i+1)%update_freq==0:
            total_loss = 0.0
            for index, batch in enumerate(test_data_loader):
                x,label = batch
                if cuda:
                    x = x.cuda()
                    label = label.cuda()
                y = model(x)
                loss = loss_func(y,label.view(-1,1))
                total_loss += float(loss.item())
            test_loss = total_loss/(index+1)
    
        if (i+1)%save_freq==0 and savepath is not None:
            torch.save(model, os.path.join(save_folder,'epoch-{}.dat'.format(i+1)))
            

def _get_parser():
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    ###########################################################################
    # Data options
    ###########################################################################
    parser.add_argument(
        "--datapath",
        type = str,
        metavar = '[str]',
        default = DATAPATH,
        help = "path to data folder"
    )
    parser.add_argument(
        "--scale-inputs",
        action="store_true",
        help = "set flag to scale input images"
    )
    parser.add_argument(
        "--workers",
        type = int,
        metavar = '[int]',
        default = WORKERS,
        help = "number of workers in DataLoader"
    )
    ###########################################################################
    # Loading/Saving
    ###########################################################################
    parser.add_argument(
        "--savepath",
        type = str,
        metavar = '[str]',
        default = SAVEPATH,
        help = "folder where model checkpoints should be saved -- if None model will not be saved "
    )
    parser.add_argument(
        "--save-freq",
        type = str,
        metavar = '[str]',
        default = SAVE_FREQ,
        help = "how often model checkpoints should be saved (in epochs) "
    )
    parser.add_argument(
        "--load-model",
        type = str,
        default = None,
        help = "Specify a saved model to load and train.  Other arguments relating to model paremeters (padding, kernel-size, etc..) will be ignored.  Training parameters (learning rate, update frequency, etc ...) may still be specified."
    )
    ###########################################################################
    # Model Architecture Options
    ###########################################################################
    parser.add_argument(
        "--conv-layers",
        type = int,
        metavar = '[int]',
        default = CONV_LAYERS,
        help = "number of Conv3d layers"
    )
    parser.add_argument(
        "--kernel-size",
        type = int,
        nargs = '+',
        metavar = 'int',
        default = KERNEL_SIZE,
        help = "kernel size of each filter"
    )
    parser.add_argument(
        "--dilation",
        type = int,
        nargs = '+',
        metavar = 'int',
        default = DILATION,
        help = "dilation factor for each filter"
    )
    parser.add_argument(
        "--padding",
        type = int,
        nargs = '+',
        metavar = 'int',
        default = PADDING,
        help = "zero padding to be used in Conv3d layers"
    )
    parser.add_argument(
        "--even-padding",
        action = "store_true",
        help = "Calculate padding vectors to ensure even perfect overlap with kernel applications.  Layers with stride = 1 will have input dimensions preserved.  The '--padding' argument is ignored when this flag is set"
    )
    parser.add_argument(
        "--stride",
        type = int,
        nargs = '+',
        metavar = 'int',
        default = STRIDE,
        help = "stride between filter applications"
    )
    parser.add_argument(
        "--filters",
        nargs = '+',
        type = int,
        metavar = 'int',
        default = [4,4,4],
        help = "filters to apply to each channel -- one entry per layer"
    )
    parser.add_argument(
        "--weight-init",
        type = str,
        metavar = '[str]',
        default = WEIGHT_INIT,
        choices = winit_funcs.keys(),
        help = "weight initialization method [{}]".format(', '.join(winit_funcs.keys()))
    )
    parser.add_argument(
        "--conv-actv",
        type = str,
        nargs = '+',
        metavar = 'str',
        default = CONV_ACTV_ARG,
        choices = actv_funcs.keys(),
        help = "activation functions to be used in convolutional layers -- must be 1 or n_conv_layers [{}]".format(', '.join(actv_funcs.keys()))
    )
    parser.add_argument(
        "--fc-actv",
        type = str,
        nargs = '+',
        metavar = 'str',
        default = CONV_ACTV_ARG,
        choices = actv_funcs.keys(),
        help = "activation functions to be used in convolutional layers -- must be 1 or n_conv_layers [{}]".format(', '.join(actv_funcs.keys()))
    )
    ###########################################################################
    #  Training Options
    ###########################################################################
    parser.add_argument(
        "--lr",
        type = float,
        metavar = '[float]',
        default = LEARNING_RATE,
        help = "learning rate paramater"
    )
    parser.add_argument(
        "--batch-size",
        type = int,
        metavar = '[int]',
        default = 32,
        help = "number of samples per batch"
    )
    parser.add_argument(
        "--epochs",
        type = int,
        metavar = '[int]',
        default = EPOCHS,
        help = "number of epochs to train over"
    )
    parser.add_argument(
        "--update-freq",
        type = int,
        metavar = '[int]',
        default = UPDATE_FREQ,
        help = "how often (in epochs) to asses test set accuracy"
    )
    parser.add_argument(
        "--cuda",
        action="store_true",
        help = "set flag to use cuda device(s)"
    )
    ###########################################################################
    # Misc. Options
    ###########################################################################
    parser.add_argument(
        "--debug-size",
        type = int,
        nargs = 4, 
        help = "Print out the expected architecture.  4 Integers should be supplied to this argument [channels, dimx, dimy, dimz].  Program execution will terminate afterwards"
    )
    parser.add_argument(
        "--silent",
        action = "store_true",
        #help = "set flag for quiet training"
        help = "NOT IMPLEMENTED"
    )

    ###########################################################################
    # not implemented
    ###########################################################################
    parser.add_argument(
        "--subpooling",
        action="store_true",
        #help = "set flag to use subpooling between Conv3d layers"
        help = "NOT IMPLEMENTED"
    )
    parser.add_argument(
        "--encode-age",
        action="store_true",
        #help = "set flag to encode age in a binary vector"
        help = "NOT IMPLEMENTED"
    )
    

    return parser

def print_network_size(args:argparse.ArgumentParser):
    padding = args.padding
    dilation = args.dilation
    kernel = args.kernel_size
    stride = args.stride
    conv_layers = args.conv_layers
    filters = args.filters
    t,x,y,z = args.debug_size

    if len(padding) == 1:
        padding = np.repeat(padding,conv_layers)
    if len(dilation) == 1:
        dilation = np.repeat(dilation,conv_layers)
    if len(kernel) == 1:
        kernel = np.repeat(kernel,conv_layers)
    if len(stride) == 1:
        stride = np.repeat(stride,conv_layers)

    conv_layer_sizes = list([np.array([x,y,z])])
    n_channels = list([t])
    for i in range(0,conv_layers):
        dims = get_out_dims(
            conv_layer_sizes[-1],
            np.repeat(padding[i],3),
            np.repeat(dilation[i],3),
            np.repeat(kernel[i],3),
            np.repeat(stride[i],3)
        ).astype(np.int16)
        idims = conv_layer_sizes[-1]
        conv_layer_sizes.append(dims)
        n_channels.append(n_channels[-1]*filters[i])

        print("Conv Layer {}: ({},{},{},{}) -> ({},{},{},{})".format(
            i,
            n_channels[-2],
            idims[0],
            idims[1],
            idims[2],
            n_channels[-1],
            dims[0],
            dims[1],
            dims[2]
        ))

    fc = int(np.prod(conv_layer_sizes[-1]))*n_channels[-1]
    print("FC layers: {} -> {} -> 100 -> 1".format(fc,int(fc/2)))


            
if __name__ == '__main__': 
    parser = _get_parser()
    args = parser.parse_args()

    if args.debug_size:
        print_network_size(args)
        exit()

    ###########################################################################
    # Loading Training Data
    ###########################################################################
    if not args.silent:
        print("Fetching training data ...")
    train_dict = get_sample_dict(
        datapath = args.datapath,
        dataset='train'
    )
    train_ages = get_sample_ages(
        ids = train_dict.keys(),
        path_to_csv = os.path.join(args.datapath,'subject_info.csv')
    )
    train_ds = NiftiDataset(
        samples = train_dict,
        labels = train_ages/100, # divide by 100 for faster learning!?
        scale_inputs = args.scale_inputs
    )

    ###########################################################################
    # Loading Testing Data
    ###########################################################################
    if not args.silent:
        print("Fetching test data ...")
    test_dict = get_sample_dict(
        datapath = args.datapath,
        dataset = 'test'
        )
    test_ages = get_sample_ages(
        ids = test_dict.keys(),
        path_to_csv = os.path.join(args.datapath,'subject_info.csv')
    )
    test_ds = NiftiDataset(
        samples = test_dict,
        labels = test_ages/100, # divide by 100 for faster learning!?
        scale_inputs = args.scale_inputs,
        cache_images = True
    )

    ###########################################################################
    # Initializing Model
    ###########################################################################
    if args.load_model is None:
        if not args.silent:
            print("Initializing model ...")
        model = MAPnet(
            input_shape = train_ds.image_shape,
            n_conv_layers = args.conv_layers,
            padding = args.padding,
            dilation = args.dilation,
            kernel = args.kernel_size,
            stride = args.stride,
            filters = args.filters,
            input_channels = train_ds.images_per_subject,
            conv_actv = [actv_funcs[x] for x in args.conv_actv],
            fc_actv = [actv_funcs[x] for x in args.fc_actv],
            even_padding = args.even_padding
        )
        ###########################################################################
        # Weight Initializaiton
        ###########################################################################
        fn = winit_funcs[args.weight_init]
        model.apply(lambda x: init_weights(x,fn))
    else:
        if not args.silent:
            print("Loading model ...")
        if not os.path.exists(args.load_model):
            raise ValueError("Cannot load model -- {} does not exist".format(args.load_model))
        model = torch.load(args.load_model)


    ###########################################################################
    # Move the model to GPU if cuda is requested
    ###########################################################################
    model = model.cuda() if args.cuda else model

    ###########################################################################
    # Print out model info ...
    ###########################################################################
    if not args.silent:
        summary(
            model,
            input_size = tuple(np.concatenate(
                [[train_ds.images_per_subject],np.array(train_ds.image_shape)]
            )),
            device = "cuda" if args.cuda else "cpu"
        )    

    ###########################################################################
    # And finally, begin training
    ###########################################################################
    train(
        train_ds,
        test_ds,
        model,
        cuda = args.cuda,
        batch_size = args.batch_size,
        num_workers = args.workers,
        epochs = args.epochs,
        update_freq = args.update_freq,
        savepath = args.savepath,
        save_freq = args.save_freq,
        optimizer = lambda x: torch.optim.Adam(x.parameters(),lr=args.lr)
    )

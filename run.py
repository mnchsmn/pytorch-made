"""
Trains MADE on Binarized MNIST, which can be downloaded here:
https://github.com/mgermain/MADE/releases/download/ICML2015/binarized_mnist.npz
"""
import argparse

import math
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
import torch.optim as optim
from torch.autograd import Variable

from made import MADE
from util import save_dict_to_json_file

# ------------------------------------------------------------------------------
def run_epoch(x, split, upto=None):
    torch.set_grad_enabled(split=='train') # enable/disable grad for efficiency of forwarding test batches
    model.train() if split == 'train' else model.eval()
    nsamples = 1 if split == 'train' else args.samples
    N,D = x.size()
    B = 100 # batch size
    nsteps = N//B if upto is None else min(N//B, upto)
    lossfs = []
    for step in range(nsteps):
        
        # fetch the next batch of data
        xb = Variable(x[step*B:step*B+B])
        
        # get the logits, potentially run the same batch a number of times, resampling each time
        xbhat = torch.zeros_like(xb)
        for s in range(nsamples):
            # perform order/connectivity-agnostic training by resampling the masks
            if step % args.resample_every == 0 or split == 'test': # if in test, cycle masks every time
                model.next_masks()
            # forward the model
            xbhat += model(xb)
        xbhat /= nsamples
        
        # evaluate the binary cross entropy loss
        loss = F.binary_cross_entropy_with_logits(xbhat, xb, size_average=False) / B
        lossf = loss.data.item()
        lossfs.append(lossf)
        
        # backward/update
        if split == 'train':
            opt.zero_grad()
            loss.backward()
            opt.step()
        
    print("%s epoch average loss: %f" % (split, np.mean(lossfs)))
    return np.mean(lossfs)
# ------------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-d', '--data-path', required=True, type=str, help="Path to binarized_mnist.npz")
    parser.add_argument('-q', '--hiddens', type=str, default='500', help="Comma separated sizes for hidden layers, e.g. 500, or 500,500")
    parser.add_argument('-n', '--num-masks', type=int, default=1, help="Number of orderings for order/connection-agnostic training")
    parser.add_argument('-r', '--resample-every', type=int, default=20, help="For efficiency we can choose to resample orders/masks only once every this many steps")
    parser.add_argument('-s', '--samples', type=int, default=1, help="How many samples of connectivity/masks to average logits over during inference")
    parser.add_argument('-p', '--patience', type=int, default=None, help="Patience for early stopping.")
    parser.add_argument('-m', '--max_epochs', type=int, default=100, help="Maximum epochs.")
    args = parser.parse_args()
    # --------------------------------------------------------------------------
    
    # reproducibility is good
    np.random.seed(42)
    torch.manual_seed(42)
    torch.cuda.manual_seed_all(42)
    
    # load the dataset
    print("loading data from", args.data_path)
    mnist = np.load(args.data_path)
    xtr, xva = mnist['train_data'], mnist['valid_data']
    # split validation set in validation + test set
    num_val = xva.shape[0] // 2
    xte = xva[:num_val,:]
    xva = xva [num_val:,:]
    xtr = torch.from_numpy(xtr).cuda()
    xva = torch.from_numpy(xva).cuda()
    xte = torch.from_numpy(xte).cuda()
    print('training_set: ' + str(xtr.shape))
    print('validation_set: ' + str(xva.shape))
    print('test_set: ' + str(xte.shape))
    # construct model and ship to GPU
    hidden_list = list(map(int, args.hiddens.split(',')))
    model = MADE(xtr.size(1), hidden_list, xtr.size(1), num_masks=args.num_masks)
    print(model)
    print("number of model parameters:",sum([np.prod(p.size()) for p in model.parameters()]))
    model.cuda()

    # set up the optimizer
    #opt = torch.optim.Adagrad(model.parameters(), lr=1e-2, eps=1e-6)
    opt = torch.optim.Adadelta(model.parameters())
    epochs_no_improve = 0
    best_loss = math.inf
    best_epoch = 0
    path = './experiments/' + args.data_path + '/'
    for n in hidden_list:
        path += '_' + str(n)
    path += '#m' + str(args.num_masks)
    path += '#s' + str(args.samples)
    params = {}
    params['layers'] = args.hiddens
    params['num_masks'] = args.num_masks
    params['samples'] = args.samples
    params['resample'] = args.resample_every
    params['patience'] = args.patience
    # start the training
    for epoch in range(args.max_epochs):
        print("epoch %d" % (epoch, ))
        run_epoch(x=xtr, split='train')
        loss = run_epoch(x=xva, split='test', upto=10) # run only a few batches for approximate test accuracy
        if loss < best_loss:
            epochs_no_improve = 0
            best_loss = loss
            best_epoch = epoch
            params['best_epoch'] = epoch
            params['best_loss'] = loss
            save_dict_to_json_file(path + '.json', params)
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': opt.state_dict(),
                'loss': loss
                }, path + ".tar")
        else:
            epochs_no_improve += 1
        last_loss = loss
        if epochs_no_improve >= args.patience:
            print("Early Stopping: No improvement for %d epochs" % (args.patience))
            break
        
    
    print("optimization done. full test set eval:")
    
    checkpoint = torch.load(path + ".tar")
    model.load_state_dict(checkpoint['model_state_dict'])
    opt.load_state_dict(checkpoint['optimizer_state_dict'])
    
    test_loss = run_epoch(x=xte, split='test')
    params['test_loss'] = test_loss
    save_dict_to_json_file(path + '.json', params)
    checkpoint['test_loss'] = test_loss
    torch.save(checkpoint, path +  ".tar")

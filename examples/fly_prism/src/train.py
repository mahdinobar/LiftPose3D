import src.utils as utils
from tqdm import tqdm
from torch.autograd import Variable
import torch.nn as nn


def train(train_loader, model, criterion, optimizer,
          lr_init=None, lr_now=None, glob_step=None, lr_decay=None, gamma=None,
          max_norm=True):
    
    losses = utils.AverageMeter()
    model.train()

    for i, (inps, tars, good_keypts, keys) in enumerate(tqdm(train_loader)):
        glob_step += 1
        if glob_step % lr_decay == 0 or glob_step == 1:
            lr_now = utils.lr_decay(optimizer, glob_step, lr_init, lr_decay, gamma)
        inputs = Variable(inps.cuda())
        targets = Variable(tars.cuda(non_blocking=True))

        #make prediction with model
        outputs = model(inputs)
        
        #evaluate high confidence keypoints only
        outputs[~good_keypts] = 0
        targets[~good_keypts] = 0
        
        # calculate loss
        optimizer.zero_grad()
        loss = criterion(outputs, targets)
        losses.update(loss.item(), inputs.size(0))
        loss.backward()
        if max_norm:
            nn.utils.clip_grad_norm(model.parameters(), max_norm=1)
        optimizer.step()

    return glob_step, lr_now, losses.avg
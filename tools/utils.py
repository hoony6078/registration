import torch
import os
import pickle
import numpy as np
import open3d as o3d

def square_distance_loss(src, dst, normalised = False):
    """
    Calculate Euclid distance between each two points.

    Input:
        src: source points, [B, N, C]
        dst: target points, [B, M, C]
    Output:
        dist: per-point square distance, [B, N, M]
    """
    
    B, N, _ = src.shape
    _, M, _ = dst.shape
    
    dist = -2 * torch.matmul(src, dst.permute(0, 2, 1))
    if(normalised):
        dist += 2
    else:
        dist += torch.sum(src ** 2, -1)[:, :, None]
        dist += torch.sum(dst ** 2, -1)[:, None, :]
        
    dist = torch.clamp(dist, min=1e-12, max=None)
    return dist

def validate_gradient(model):
    """
    Confirm all the gradients are non-nan and non-inf
    """
    for name, param in model.named_parameters():
        if param.grad is not None:
            if torch.any(torch.isnan(param.grad)):
                return False
            if torch.any(torch.isinf(param.grad)):
                return False
    return True

def load_obj(path):
    """
    read a dictionary from a pickle file
    """
    with open(path, 'rb') as f:
        return pickle.load(f)

def save_obj(obj, path ):
    """
    save a dictionary to a pickle file
    """
    with open(path, 'wb') as f:
        pickle.dump(obj, f)

def to_tsfm(rot,trans):
    
    tsfm = np.eye(4)
    tsfm[:3,:3] = rot
    tsfm[:3,3] = trans.flatten()
    return tsfm

def to_tensor(x):
    """
    Conver array to tensor 
    """
    if isinstance(x, torch.Tensor):
        return x
    elif isinstance(x, np.ndarray):
        return torch.from_numpy(x)
    else:
        raise ValueError(f'Can not convert to torch tensor, {x}')



def to_array(tensor):
    """
    Conver tensor to array
    """
    if(not isinstance(tensor,np.ndarray)):
        return tensor.cpu().numpy()
    else:
        return tensor

def to_o3d_pcd(xyz):
    """
    Convert tensor/array to open3d PointCloud
    xyz:       [N, 3]
    """
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(to_array(xyz))
    return pcd

class Logger:
    def __init__(self, path):
        self.path = path

        os.makedirs(self.path, exist_ok=True)

        self.fw = open(self.path+'/log','a')

    def write(self, text):
        self.fw.write(text)
        self.fw.flush()

    def close(self):
        self.fw.close()

def get_correspondences(src_pcd, tgt_pcd, trans, search_voxel_size, K=None):
    src_pcd.transform(trans)
    pcd_tree = o3d.geometry.KDTreeFlann(tgt_pcd)

    correspondences = []
    for i, point in enumerate(src_pcd.points):
        [count, idx, _] = pcd_tree.search_radius_vector_3d(point, search_voxel_size)
        if K is not None:
            idx = idx[:K]
        for j in idx:
            correspondences.append([i, j])
    
    correspondences = np.array(correspondences)
    correspondences = torch.from_numpy(correspondences)
    return correspondences

from cmath import inf
from zipfile import ZipFile
import wget
import os
import json
import glob
import cv2
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split

def download_zip():
    print('Downloading zip files...')

    url1 = 'https://zenodo.org/record/4570965/files/Glenda_v1.5_classes.zip?download=1'
    url2 = 'https://zenodo.org/record/4570965/files/GLENDA_v1.5_no_pathology.zip?download=1'

    wget.download(url1)
    wget.download(url2)

    print('Finished downaloading!')

def extract_zip():
    file_name = "Glenda_v1.5_classes.zip"

    with ZipFile(file_name,'r') as zip:
        zip.printdir()

        print('\nExtracting all files from', file_name,'...')
        zip.extractall()
        print('Finished extracting!\n')
    
    file_name = "GLENDA_v1.5_no_pathology.zip"

    with ZipFile(file_name,'r') as zip:
        zip.printdir()

        print('\nExtracting all files from', file_name,'...')
        zip.extractall()
        print('Finished extracting!\n')

def delete_zip():
    print('Deleting .zip files...')

    os.remove('Glenda_v1.5_classes.zip')
    os.remove('GLENDA_v1.5_no_pathology.zip')

    print('Finished deleting!')

def find_common_image_dim():
    coco = json.load(open('Glenda_v1.5_classes/coco.json'))
    wxh_list = []
    label = []
    # record all image dimensions and find the most common image dimension
    for dic in coco["annotations"]:
        width = dic["width"]
        height = dic["height"]
        label.append(int(dic["category_id"])-1) # converting to label starting from 0
        wxh_list.append('{0:d}x{1:d}'.format(width,height))
    wxh = max(set(wxh_list), key=wxh_list.count).split('x')
    width, height = wxh[0], wxh[1]

    return int(width), int(height)

def extract_img_masks(width, height):
    #Capture images 
    image = []
    mask = []
    """
    Images and masks are aligned in order so we do not have to use coco.json to find the corresponding annotations
    """
    # Extract all images, read it wwith colour scale and resize it -> convert to np.array
    for directory_path in glob.glob('Glenda_v1.5_classes/frames/'):
        for img_path in glob.glob(os.path.join(directory_path, "*.jpg")):
            img = cv2.imread(img_path, 0) # pass 0 for grayscale, in this case 1 for colour images       
            img = cv2.resize(img, (width, height)) # Resizing all images to the most common dimension
            #img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
            image.append(img)
    image = np.array(image)

    # Extract all masks, read it wwith colour scale and resize it -> convert to np.array
    for directory_path in glob.glob('Glenda_v1.5_classes/annots/'):
        for img_path in glob.glob(os.path.join(directory_path, "*.png")):
            msk = cv2.imread(img_path, 0) # pass 0 for grayscale, in this case 1 for colour images       
            msk = cv2.resize(msk, (width, height)) # Resizing all images to the most common dimension
            #msk = cv2.cvtColor(msk, cv2.COLOR_BGR2RGB)
            mask.append(msk)
    mask = np.array(mask)
    return image, mask

def label_msk(mask, n_classes):
    # mask have different color in the boundary making the pixel label not consistent, thus, by selecting the top n_classes
    # frequent color as the standard and eliminates all other color in the mask. 
    color = []
    unique, counts = np.unique(mask, return_counts=True)
    for i in range(n_classes):
        idx = np.argmax(counts)
        color.append(unique[idx])
        unique = np.delete(unique, idx)
        counts = np.delete(counts, idx)

    num, height, width = mask.shape
    for n in range(num):
        for h in range(height):
            for w in range(width):
                if mask[n,h,w] not in color:
                    mask[n,h,w] = 0
    
    labelencoder = LabelEncoder()
    mask = mask.reshape(-1,1)
    mask = labelencoder.fit_transform(mask)
    mask = mask.reshape(num, height, width)

    return mask

def split_data(image, mask):
    x1, x_test, y1, y_test = train_test_split(image, mask, test_size = 0.10, random_state = 0)

    #Further split training data t a smaller subset for quick testing of models
    x_train, x_valid, y_train, y_valid = train_test_split(x1, y1, test_size = 0.2, random_state = 0)

    return x_train, x_test , x_valid, y_train, y_test, y_valid

def data_loader(n_classes = 5):
    # check if directory exists
    path_Glenda = os.path.isdir('Glenda_v1.5_classes')
    path_pathology = os.path.isdir('no_pathology')
    # if either one is not existed, dowwnload the file
    if (not path_Glenda) or (not path_pathology):
        download_zip()
        extract_zip()
        delete_zip()
    else:
        print('file exists')
    
    # find most common image dimensions
    width, height= find_common_image_dim()
    image, mask = extract_img_masks(width, height)
    #image = normalize(image, axis=1)
    mask = label_msk(mask, n_classes)
    image = np.expand_dims(image, axis=3) # expanding to fit the input of model
    image = image/255 # making the value within the image from 0~1
    mask = np.expand_dims(mask, axis=3)
    x_train, x_test , x_valid, y_train, y_test, y_valid = split_data(image, mask)
    return x_train, x_test , x_valid, y_train, y_test, y_valid

if __name__ == "__main__":
    data_loader()
    

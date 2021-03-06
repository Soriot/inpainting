# -*- coding: utf-8 -*-
"""
Created on Wed Apr 25 17:09:30 2018

@author: kouassi
Performance evaluation of test dataset prediction
"""

from sklearn.metrics import mean_squared_error as rmse1
import numpy as np
import xarray as xr
import numpy.core.numeric as _nx
from numpy.core.numeric import  isnan
from numpy import isneginf, isposinf
from copy import copy
import matplotlib.pyplot as plt 
from scipy import fftpack


def mask_apply(y_true, y_pred):
    """ Application du masque pour travailler uniquement sur 
    le carré imputé par le réseau de neurone profond.
    y_true_m et y_pred_m sont uniquement le carré ou la forme imputée 
    par le reseau de neurone profond. 
    y_true et y_pred sont le carré ou la forme imputée 
    par le reseau de neurone profond , entouré par zero pour le reste de l'imagette."""
    nanval = -1e5
    # Réduction de dimension un array 2d (64*64)
    if y_true.ndim>2:
        y_true = np.squeeze(y_true)
    if y_pred.ndim>2:
        y_pred = np.squeeze(y_pred)
    # Définition et binarisation du masque
    isMask = np.empty_like(y_true)
    isMask[y_true == nanval] = 0
    isMask[y_true != nanval] = 1
    # Application du masque sur les y_true et y_pred
    y_true = y_true * isMask;
    y_pred = y_pred * isMask;
    y_true_m = y_true[y_true != 0]
    y_pred_m = y_pred[y_true != 0]
    return y_true, y_pred, y_true_m, y_pred_m

def mask_apply_crop(y_true, y_pred, cwidth, cheight, cb):
    """ Cette fonction est utilisée uniquement à l'étape d'évaluation des performances
    du réseau (Phase de Post-traitement).
    Cette fonction permet de selectionner les ytrue et ypred qu'on 
    veut selon la position dans l'image du carré dans l'image.
        - cheight : est la hauteur à prendre ou pas  en compte.
        - cwidth :  est la largeur à prendre ou pas en compte.
        - cb : booléen : if [True : crop extérieur] et [False : crop intérieur] """
    nanval = -1e5
    # Définition et binarisation du masque
    isMask = np.empty_like(y_true)
    isMask[y_true == nanval] = 0
    isMask[y_true != nanval] = 1
    # Reduction de dimension de (64*64*1) à (64*64)
    if y_true.ndim>2:
        isMask = np.squeeze(isMask)
        y_true = np.squeeze(y_true)
    if y_pred.ndim>2:
        y_pred = np.squeeze(y_pred)
    # Mask de selection des y true à plotter
    if (cb == True):
        bigmask = np.zeros(shape=(64,64))
        bigmask[cwidth:-cwidth, cheight:-cheight] = 1  
        isMask1 = isMask * bigmask
    elif (cb == False):
        bigmask = np.ones(shape=(64,64))
        bigmask[cwidth:-cwidth, cheight:-cheight] = 0  
        isMask1 = isMask * bigmask   
    # Application du masque sur 
    y_true = y_true * isMask1
    y_pred = y_pred * isMask1
    y_true_m = y_true[y_true != 0]
    y_pred_m = y_pred[y_true != 0]
    return y_true, y_pred, y_true_m, y_pred_m


def test_masked_mse(y_true, y_pred, amask, nmask, dx=2, dy=0, coefC=0.1, coefN=1 ):
    """ Calcul du loss par root mean square (sklearn) en attribuant des coefficients
    de pondération différents: 
    - coefN pour le contour extrait par nmask (neighbor mask) et 
    - coefC pour la région à completer, extraite par amask. """
    #data\cloud
    ytr, ypr, y_tr_m, y_pr_m = mask_apply(y_true,y_pred)
    if (dx==0 and dy==0):
        mseLoss = rmse1(y_tr_m, y_pr_m)
    elif (dx>0 or dy>0):
        if nmask.ndim>2:
            nmask = np.squeeze(nmask)
        nmask = np.logical_not(nmask) # Cette transformation permet de 
        LossC = rmse1(ytr*amask, ypr*amask)
        LossN = rmse1(ytr*nmask, ypr*nmask)
        mseLoss = coefC*LossC + coefN*LossN
    return mseLoss

def test_masked_corrcoef(y_true,y_pred):
    """calcul du coefficient de correlation entre chla predict et chla true 
    du carré imputé par le reseau de neurones profond. """
    ytr, yp, y_tr_m, y_pr_m = mask_apply(y_true,y_pred)
    CorrCoef = np.corrcoef(y_tr_m, y_pr_m, bias=True)[0][1]
    return CorrCoef

def test_pixel_masked_loss(y_true, y_pred):
    ytrue, ypred, ytrue_m, ypred_m = mask_apply(y_true,y_pred)
    i = np.where(ytrue != 0)
    index_dim = np.shape(i)
    i_center = int(index_dim[1]/2) # indice de l'indice central du mask
    b = np.subtract(ytrue, ypred)
    # pixel central
    ix_center = i[0][i_center]
    iy_center = i[1][i_center]
    chla_center = b[ix_center,iy_center]
    # pixel central supérieur
    ix_up = i[0][0]
    #chla_upcenter = b[ix_up,iy_center]
    # pixel central inférieur
    ix_down = i[0][-1]
    #chla_DC = b[ix_down,iy_center]
    # pixel central gauche
    iy_left = i[1][0]
    #chla_LC = b[ix_center,iy_left]
    # pixel central droit
    iy_right = i[1][-1]
    #chla_RC = b[ix_center,iy_right]
    # pixel  des coins 
    chla_UL = b[ix_up,iy_left]       # coin supérieur gauche
    chla_UR = b[ix_up,iy_right]      # coin supérieur droit
    chla_DL = b[ix_down, iy_left]    # coin inférieur gauche
    chla_DR = b[ix_down, iy_right]   # coin inférieur droit 
    return chla_center, chla_UL, chla_UR, chla_DL, chla_DR

def azimuthalAverage(image, center=None):   
    """ This function comes from "radialProfile.py".
	Calculate the azimuthally averaged radial profile.
    image - The 2D image
    center - The [x,y] pixel coordinates used as the center. The default is 
             None, which then uses the center of the image (including 
             fractional pixels). """
    # Calculate the indices from the image
    A = np.indices(image.shape)
    y = A[0,:,:] ; x = A[1,:,:]
    if not center:
        center = np.array([(x.max()-x.min())/2.0, (x.max()-x.min())/2.0])
    r = np.hypot(x - center[0], y - center[1])
    # Get sorted radii
    ind = np.argsort(r.flat)
    r_sorted = r.flat[ind]
    i_sorted = image.flat[ind]
    # Get the integer part of the radii (bin size = 1)
    r_int = r_sorted.astype(int)
    # Find all pixels that fall within each radial bin.
    deltar = r_int[1:] - r_int[:-1]  # Assumes all radii represented
    rind = np.where(deltar)[0]       # location of changed radius
    nr = rind[1:] - rind[:-1]        # number of radius bin
    # Cumulative sum to figure out sums for each radius bin
    csim = np.cumsum(i_sorted, dtype=float)
    tbin = csim[rind[1:]] - csim[rind[:-1]]
    radial_prof = tbin / nr
    return radial_prof

def inpainted_region(inputTestName, outputTestName ):
    #outputTestName = '../data/cloud/DatasetNN_cloud.nc'
    #inputTestName = '../data/cloud/BaseTest_cloud.nc'
    inputTest = xr.open_dataset(inputTestName)
    outputTest = xr.open_dataset(outputTestName)
    Amask = np.array(inputTest.amask, dtype = int)
    chla_finalV = outputTest.yfinal.values.squeeze()
    CHLAFC = [] ;   # initialisation
    for i in range(chla_finalV.shape[0]):
        chla_F = chla_finalV[i,:,:]; amask = Amask[i,:,:]
        idx = np.argwhere(amask==1) 
        # Coordonnées des 4 extremités de la région contenant celle completée
        ind_x_TL = np.argmin(idx[:,0], axis=0); x_TL = idx[ind_x_TL,0]
        ind_x_DR = np.argmax(idx[:,0], axis=0); x_DR = idx[ind_x_DR,0]
        ind_y_TL = np.argmin(idx[:,1], axis=0); y_TL = idx[ind_y_TL,1]
        ind_y_DR = np.argmax(idx[:,1], axis=0); y_DR = idx[ind_y_DR,1]
        # Calcul de la hauteur et de la largeur de cette région
        width = 1 + np.subtract(y_DR , y_TL) 
        height = 1 + np.subtract(x_DR, x_TL) 
        # Reconstruction de la region contenant la region completée
        chlaFC = np.empty(shape=(height,width), dtype=float)
        chlaFC = chla_F[x_TL:x_TL+height, y_TL:y_TL+width]
        CHLAFC.append(chlaFC.tolist())
        CHLAFC = CHLAFC
    return CHLAFC, chla_finalV

def power_spectrum(inputTestName, outputTestName, cb=True,plot = True):
    """ cb : True if the spectrum is computed on the whole chla_final image
        cb : False if teh sppectrum is computed only on the restricted area contianing 
             the inpainted image.
        plot= True enables the visualization of 20 images sampled randomly.
        plot = False disables the visualization of 20 images sampled randomly. """
    #outputTestName = '../data/cloud/DatasetNN_cloud.nc'
    #inputTestName = '../data/cloud/BaseTest_cloud.nc'
    PSD2D = [] ;PSD1D = []
    if cb == True:
        outputTest = xr.open_dataset(outputTestName)
        chla_final = outputTest.yfinal.values.squeeze()
        for i in range(chla_final.shape[0]):
            chlaF = chla_final[i,:,:]
            # CALCUL DU SPECTRE DE PUISSANCE 
            # Take the fourier transform of the image.
            F1 = fftpack.fft2(chlaF)
            # Now shift the quadrants around so that low spatial frequencies are in
            # the center of the 2D fourier transformed image.
            F2 = fftpack.fftshift( F1 )
            # Calculate a 2D power spectrum
            psd2D = np.abs( F2 )**2
            PSD2D.append(psd2D.tolist())  # array contenant les a 2D power spectrum
            # Calculate the azimuthally averaged 1D power spectrum
            psd1D = azimuthalAverage(psd2D)
            PSD1D.append(psd1D.tolist())   
        if plot ==True:
            # Visualisation de 20 images tirées aléatoirement 
            nim = 20
            idx = np.random.randint(0,chla_final.shape[0], nim)
            for i,ind in enumerate(idx):
                fig, ax = plt.subplots(ncols=3)
                ax[0].imshow(np.log10(chla_final[ind,:,:]))
                ax[1].imshow(np.log10(np.array(PSD2D[ind])))
                ax[2].plot(PSD1D[ind])
        
    elif cb == False :   
        CHLAFC , chla_finalV = inpainted_region(inputTestName, outputTestName)
        for i in range(chla_finalV.shape[0]):
            chlaFC = np.array(CHLAFC[i])
            # CALCUL DU SPECTRE DE PUISSANCE 
            # Take the fourier transform of the image.
            F1 = fftpack.fft2(chlaFC)
            # Now shift the quadrants around so that low spatial frequencies are in
            # the center of the 2D fourier transformed image.
            F2 = fftpack.fftshift( F1 )
            # Calculate a 2D power spectrum
            psd2D = np.abs( F2 )**2
            PSD2D.append(psd2D.tolist())  # array contenant les a 2D power spectrum
            # Calculate the azimuthally averaged 1D power spectrum
            psd1D = azimuthalAverage(psd2D)
            PSD1D.append(psd1D.tolist())   
        if plot ==True :
            # Visualisation de 20 images tirées aléatoirement
            nim = 20
            ii = np.random.randint(0,chla_finalV.shape[0], nim)
            for i,ind in enumerate(ii):
                fig, ax = plt.subplots(ncols=3)
                ax[0].imshow(np.array(CHLAFC[ind]))
                ax[1].imshow(np.log10( np.array(PSD2D[ind]) ))
                ax[2].plot(PSD1D[ind])
        
    else :
        print("cb est un booléen ! ")
    return PSD2D, PSD1D



def getmaxmin(t):
    from numpy.core import getlimits
    f = getlimits.finfo(t)
    return f.max, f.min

def nan_to_nanval(x,nanval=-1e5):
    x = _nx.array(x, subok=True)
    xtype = x.dtype.type
    if not issubclass(xtype, _nx.inexact):
        return x
    iscomplex = issubclass(xtype, _nx.complexfloating)
    isscalar = (x.ndim == 0)
    x = x[None] if isscalar else x
    dest = (x.real, x.imag) if iscomplex else (x,)
    maxf, minf = getmaxmin(x.real.dtype)
    for d in dest:
        _nx.copyto(d, nanval, where=isnan(d))
        _nx.copyto(d, maxf, where=isposinf(d))
        _nx.copyto(d, minf, where=isneginf(d))
    return x[0] if isscalar else x

def mask_builder(testDataSet,maskBasename):
    #testDataSet = '../data/cloud/BaseTest_cloud.nc'
    #maskBaseName = '../data/cloud/maskTest_cloud.nc'
    ds = xr.open_dataset(testDataSet)
    am = np.array(ds.amask.values, dtype=float) 
    cm = np.array(ds.cmask.values, dtype=float) 
    nm = np.asarray(ds.amask.values, dtype=float)
    nm = np.add(am,cm); # Creation du masque
    nm[np.where(nm==1)] = 2
    nm[np.where(nm==0)] = 1
    nm[np.where(nm==2)] = 0 
    # remplacement des nan en nanval=-1e5 des yt (necessaire pour le recherche d'index)
    nanval = -1e5
    YT = ds['yt']; yt_values = copy(ds.yt.values); yt_values= nan_to_nanval(yt_values,nanval=nanval)
    YT.values = yt_values
    # Stockage dans une base de données
    AM = ds['amask']; AM.values = am;
    NM = ds['nmask']; NM.values = nm
    mds = xr.Dataset({'X':(['index','y','x'],ds.X),
                                       'yt':(['index','y','x'],YT),
                                       'amask':(['index','y','x'],AM),
                                       'nmask':(['index','y','x'],NM)},
                                        coords = ds.coords)  
    mds.to_netcdf(maskBasename)
    return mds

def index_search(ytrue,maskds):
    nanval = -1e5
    ytrue = nan_to_nanval(ytrue, nanval=nanval)
    count =0 ; ind11=None
    YT = maskds.yt.values; YTvalues=YT[count,:,:]
    # création d'un masque
    ytruem = ytrue[np.where(YTvalues!=nanval)]
    YTvaluesm = YTvalues[np.where(YTvalues!=nanval)]
    comp = np.array_equal(ytruem, YTvaluesm);
    if comp==True:
        ind11 = count
        
    elif comp==False: 
        while (comp==False and count<-1+maskds.X.values.shape[0]):
            count+=1
            YTvalues=YT[count,:,:];
            YTvaluesm = YTvalues[np.where(YTvalues!=nanval)]
            ytruem = ytrue[np.where(YTvalues!=nanval)]
            comp = np.array_equal(ytruem, YTvaluesm)
            if comp == True:
                ind11 = copy(count)
                break
            print(count)
    ind1 = copy(ind11)
    return ind1
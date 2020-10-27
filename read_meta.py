# display Tangerine-related meteadata in the drf_properties.h5 file
import h5py 
metadataPath = "/media/ubuntu/tangerine1/hdf5"
f5 = h5py.File(metadataPath + '/drf_properties.h5','r+')
chf = f5.attrs.__getitem__('subchannel_frequencies_MHz')
t = f5.attrs.__getitem__('data_source')
ant = f5.attrs.__getitem__('antenna_ports')
f5.close()
print('chf=',chf)
print('ant=',ant)
print("source=",t)

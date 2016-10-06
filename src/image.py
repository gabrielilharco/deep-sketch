import numpy as np
import scipy as sp
from PIL import Image, ImageOps
from scipy import ndimage

def display_random_image(root, class_name=None):
	"""
	display a random image in a root directory.
	class_name is the name of the subdirectory
	if class_name is set to None, then a random folder is chosen
	"""
	if class_name is None:
		class_name = np.random.choice(os.listdir(root))
	print('Showing image of class <%s>' % class_name)
	folder = os.path.join(root, class_name)
	image_file = np.random.choice(os.listdir(folder))
	image = Image.open(os.path.join(folder,image_file))
	image.show()

def scale_and_trim(image_file, width, height, padding=0):
	"""
	scale image to a given width and height.
	the first step is to find a boundbox containing the actual drawing in the image
	after that, just a simple scaling, considering padding if it is the case
	"""
	# actual width and height we need to re-scale to
	w = width-2*padding
	h = height-2*padding
	# read image
	image = Image.open(image_file)
	# trimming
	xstart, ystart, xend, yend = ImageOps.invert(image).getbbox()
	trimmed_image = image.crop((xstart, ystart, xend, yend))
	# scale 
	scale_factor = min(float(w)/(yend-ystart), float(h)/(xend-xstart))
	size = (int(scale_factor*(xend-xstart)), int(scale_factor*(yend-ystart)))
	trimmed_image.thumbnail(size, Image.ANTIALIAS)
	# expanding
	t_w, t_h = trimmed_image.size
	scaled_image = Image.new('L', (width, height), color=255)
	offset = ((width-t_w)/2, (height-t_h)/2)
	scaled_image.paste(trimmed_image, offset)
	# returning
	return np.asarray(scaled_image)

def compute_gradient(image):
	"""
	compute gradient and its orientation for each pixel of an image using the Sobel operator
	"""
	# horizontal and vertical derivatives
	gx = ndimage.sobel(image, 0)
	gy = ndimage.sobel(image, 1)
	# gradient magnitude
	g = np.hypot(gx, gy)
	# gradient direction between -pi and pi
	theta = np.arctan2(gx, gy)
	# making theta fit in [0,pi]
	theta[theta < 0] += np.pi
	return g, theta

def bin_orientation(grad, theta, n_bins=4):
	"""
	bin orientation reponse in <n_bins> bins, linearly interpolating between bins
	"""
	responses = np.ndarray(shape=(n_bins, grad.shape[0], grad.shape[1]), dtype=np.float32)	
	# assumes angles are always in [0,pi]
	bin_size = np.pi/n_bins
	for i in range (n_bins):
		bin_center = bin_size*(i+0.5)
		# mask for linear interpolation
		mask = np.maximum(0, (1-abs(theta-bin_center)/bin_size)) 
		responses[i] = np.multiply(grad,mask)
	return responses

def build_local_descriptor(orientation_responses, position, size, n_spatial_bins=4):
	"""
	build local descriptor at a given position using orientational responses, binning spatial data using linear interpolation
	"""	
	try:
		# relevant parts of the orientational response
		local_orientation_responses = orientation_responses[:, int(position[0]-size/2):int(position[0]+size/2), int(position[1]-size/2):int(position[1]+size/2)]
	except IndexError:
		# TODO: refactor to allow this
		print('Invalid set of position and size.')
	else:
		# create 2d tent for convolution
		# the tent should have the size of 2 times the size of the bin
		bin_size = size/n_spatial_bins
		tent = np.fromfunction(lambda i, j: np.maximum(0, np.minimum((1-abs(i-bin_size)/bin_size),(1-abs(j-bin_size)/bin_size))), (2*bin_size+1, 2*bin_size+1), dtype=np.float32)
		# TODO: try gaussian?
		# convolve with 2d tent
		convolved_responses = np.ndarray(shape=(local_orientation_responses.shape), dtype=np.float32)	
		for i in range(len(local_orientation_responses)):
			convolved_responses[i] = ndimage.convolve(local_orientation_responses[i], tent, mode='constant', cval=0.0)
		# now the binned response is just  a lookup at the center of the bin
		binned_response = convolved_responses[:, bin_size/2:size:bin_size, bin_size/2:size:bin_size]
		# TODO: normalize?
		return binned_response

def build_local_descriptors(orientation_responses, n_samples, patch_size, n_spatial_bins=4):
	"""
	buld all local descriptors using the orientational responses, at n_samples x n_samples equally spaced positions
	"""
	local_descriptors = set()
	step_size = orientation_responses.shape[1]/n_samples
	for i in range(0, n_samples):
		for j in range(0, n_samples):
			position = ((i+0.5)*step_size, (j+0.5)*step_size)
			local_descriptor = build_local_descriptor(orientation_responses, position, patch_size, n_spatial_bins)
			local_descriptors.add(tuple(local_descriptor.flatten()))
	return local_descriptors

def get_descriptors(images):
	return images


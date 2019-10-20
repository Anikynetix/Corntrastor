'''
Created on Sep 18, 2019

@author: Anik
'''

from matplotlib import style
from numpy import ones, vstack
from numpy.linalg import lstsq, norm
from os import listdir
from os.path import isfile, join
from PIL import Image, ImageEnhance
from skimage.color import rgb2gray
from sklearn.cluster import KMeans
from skimage.io import imread
from statistics import mean
import colorsys, matplotlib.pyplot, numpy, os, pygame, sys

INPUTFOLDERNAME = "raw_images"
INTERMEDFOLDERNAME = "processed_images"
OUTPUTFOLDERNAME = "filtered_images"
ROWS = 4

pygame.init()


# Class for adjusting image level
class Level(object):
    
    # Constructor
    def __init__(self, minv, maxv, gamma):
        
        self.minv = minv / 255.0
        self.maxv = maxv / 255.0
        self._interval = self.maxv - self.minv
        self._invgamma = 1.0 / gamma

    # Obtain level value
    def newLevel(self, value):
        
        if value <= self.minv: return 0.0
        if value >= self.maxv: return 1.0
        
        return ((value - self.minv) / self._interval) ** self._invgamma

    # Level and convert the image tp RGB
    def convertAndLevel(self, band_values):
        
        h, s, v = colorsys.rgb_to_hsv(*(i / 255.0 for i in band_values))
        new_v = self.newLevel(v)
        
        return tuple(int(255 * i)
                for i
                in colorsys.hsv_to_rgb(h, s, new_v))
        

# Class for handling image files
class File(object):
    
    # Constructor
    def __init__(self, inF, outF):
        
        self.inF = inF
        self.outF = outF
    
    # Returns a list of filenames in the Input Folder
    def getFilenames(self):
        
        if not os.path.isdir(self.inF):
            
            os.makedirs(self.inF)
            
        return [f for f in listdir(self.inF) if isfile(join(self.inF, f))]
    
    # Returns a list of image objects in the input folder
    def getImages(self):
        
        filenames = self.getFilenames()
        imageList = []
        
        for file in filenames:
            
            imageList.append(self.openImg(self.inF + "/" + file))
        
        return imageList

    # Returns a list of sci-kit image objects in the input folder
    def getSKImages(self):
        
        filenames = self.getFilenames()
        imageList = []
        
        for file in filenames:
            
            imageList.append(self.openSKImg(self.inF + "/" + file))
        
        return imageList
    
    # Saves a list of image objects as image in the output folder
    def setImages(self, imageList):
        
        if not os.path.isdir(self.outF):
            
            os.makedirs(self.outF)
        
        for i, img in enumerate(imageList):
            
            img.save(self.outF + "/{:03d}.png".format(i))
    
    # Saves a list of sci-kit image objects as image in the output folder
    def setSKImages(self, imageList):
        
        if not os.path.isdir(self.outF):
            
            os.makedirs(self.outF)
        
        for i, img in enumerate(imageList):
            
            matplotlib.pyplot.imsave((self.outF + "/{:03d}.png".format(i)), img, cmap='gray')
    
    # Returns a single image object
    def openImg(self, fileName):
        
        img = None
        
        try:
            
            img = Image.open(fileName)
            
        except FileNotFoundError:
            
            print ("Invalid filename")
        
        return img
    
    # Returns a single sci-kit image object
    def openSKImg(self, fileName):
        
        img = None
        
        try:
            
            img = imread(fileName)
            
        except FileNotFoundError:
            
            print ("Invalid filename")
        
        return img


# Class for trimming and resizing image
class Trim(object):
    
    # Constructor
    def __init__(self, maxWhiteThresh, rowHeight):
        
        self.maxWhiteThresh = maxWhiteThresh
        self.rowHeight = rowHeight
    
    # Naive trimming that trims the top and the bottom of the image by a fixed amount
    def naiveTrim(self, img, topTrim, bottomTrim):
    
        width, height = img.size
        
        left = 0
        right = width
        top = int(height * topTrim)
        bottom = int(height * bottomTrim)
        
        return img.crop((left, top, right, bottom))
    
    # Smart trimming that trims the top and the bottom of the image based on pixel density of each row 
    def smartTrim(self, img):
        
        width = img.size[0]
        
        left = 0
        right = width
        top = self.getTop(img)
        bottom = self.getBottom(img)
        
        return img.crop((left, top, right, bottom))
    
    # Compares each single pixel row of the image starting from the top with the threshold, and returns the distance from the top when the white pixel density falls below the threshold
    def getTop(self, img):
        
        width, height = img.size
        
        left = 0
        right = width
        
        for i in range (int(height / (2 * self.rowHeight)) - 1):
            
            rowImg = img.crop((left, i * self.rowHeight, right, (i + 1) * self.rowHeight))
            pixels = rowImg.getdata()
            
            whiteThresh = 50
            count = 0
            
            for pixel in pixels:
                
                if pixel > whiteThresh:
                    
                    count += 1
                    
            n = len(pixels)
            
            if (count / float(n)) < self.maxWhiteThresh:
                
                return ((i + 1) * self.rowHeight)
            
        return  (int(height / 2) - 1)
    
    # Compares each single pixel row of the image starting from the bottom with the threshold, and returns the distance from the top when the white pixel density falls below the threshold
    def getBottom(self, img):
        
        width, height = img.size
        
        left = 0
        right = width
        
        for i in range (int(height / (2 * self.rowHeight)) - 1):
            
            rowImg = img.crop((left, height - ((i + 1) * self.rowHeight), right, height - (i * self.rowHeight)))
            pixels = rowImg.getdata()
            
            whiteThresh = 50
            count = 0
            
            for pixel in pixels:
                
                if pixel > whiteThresh:
                    
                    count += 1
                    
            n = len(pixels)
            
            if (count / float(n)) < self.maxWhiteThresh:
                
                return (height - ((i + 1) * self.rowHeight))
            
        return  (int(height / 2) + 1)


# Class for fitting lines in a cluster of points
class Line(object):
    
    # Constructor
    def __init__(self):
        
        self.dummy = None
    
    # Returns the gradient and the intercept of a line equation
    def getLineEq(self, segment):
        
        x_coords, y_coords = zip(*segment)
        A = vstack([x_coords, ones(len(x_coords))]).T
        m, c = lstsq(A, y_coords)[0]
        
        print("Line Solution is y = {m}x + {c}".format(m=m, c=c))
    
    # Returns the distance between a point and a line segment
    def getShortestDist(self, point, segment):
        
        # Convert the points coordinates to numpy array
        p1 = numpy.array(segment[0])
        p2 = numpy.array(segment[1])
        p3 = numpy.array(point)
        
        # Calculate the shortest distance from a point to a line segment 
        return norm(numpy.cross(p2 - p1, p1 - p3)) / norm(p2 - p1)
    
    # Fits a line in a subset of points that reside between a starting value and an ending value of y
    def getBestFit(self, points, start, end, height):
        
        # Initialize the minimum distance as infinity
        minDist = [(-1, -1), (-1, -1), sys.maxsize, -1]
        
        # For each pixel in the top row, iterate through each pixel in the bottom row
        for i in range(end - start):
            
            for j in range(end - start):
                
                # Initialize sum variables
                totalDist = 0
                pointCount = 0
                
                for point in points:
                    
                    # dist = self.getShortestDist(point, [(0, i + start), (height, j + start)]) * abs(((end - start) / 2) - point[1])
                    dist = self.getShortestDist(point, [(0, i + start), (height, j + start)])
                    
                    totalDist += dist
                    pointCount += 1
                
                # Check and update minimum distance if necessary
                if totalDist < minDist[2]:
                    
                    # Update top point, bottom point, sum of all distances between all the points and the line segment, and deviation
                    minDist = [(0, i + start), (height, j + start), totalDist, pow(2, totalDist / pointCount) / 10]
        
        print("Best Fit Strip : ", minDist)
        return [minDist[0], minDist[1]]
    
    # Fits a line in a subset of points that reside between a starting value and an ending value of y
    def getStrictFit(self, points, rows, height, width):
        
        # Calculate the width of each strip
        stripWidth = round(width / rows)
        
        # Initialize the minimum distance as infinity
        minDist = [(-1, -1), (-1, -1), sys.maxsize]
        
        subPoints = []
        
        # Group the points into their respective strips
        for i in range(rows):
            
            subPoints.append(self.getSubPoints(points, i * stripWidth, (i + 1) * stripWidth))
        
        for i in range(stripWidth):
            
            for j in range(stripWidth):
                
                # Initialize sum variables
                totalDist = 0
                pointCount = 0
                
                firstLineY = i
                lastLineY = j + (stripWidth * (rows - 1))
                
                lineGap = (lastLineY - firstLineY) / (rows - 1)
                
                linesY = []
                
                for k in range (rows):
                    
                    linesY.append(firstLineY + (k * lineGap))
                
                for k in range (rows):
                    
                    subDist = 0
                    subCount = 0
                    
                    for subpoint in subPoints[k]:
                        
                        dist = self.getShortestDist(subpoint, [(0, linesY[k]), (height, linesY[k])])
                        
                        subDist += dist
                        subCount += 1
                        
                        totalDist += dist
                        pointCount += 1
                
                # Check and update minimum distance if necessary
                if totalDist < minDist[2]:
                    
                    # Update Y coordinates of first line, last line and sum of all distances between all the points and the line segment
                    minDist = [firstLineY, lastLineY, totalDist]
        
        print("Strict Fit Range : ", minDist)
        return [minDist[0], minDist[1]]
    
    # Gets the coordinates of all the white pixels in the image
    def getPoints(self, img):
        
        points = []
        
        row = len(img)
        col = len(img[0])
        
        for i in range(row):
            
            for j in range(col):
                
                # Check for white pixel
                if img[i][j][0] == 255:
                    
                    points.append((i, j))
        
        return points
    
    # Gets the coordinates of all the white pixels in the image that reside between a starting value and an ending value of y
    def getSubPoints(self, points, start, end):
        
        subPoints = []
        
        for point in points:
            
            if point[1] >= start and point[1] < end:
                
                subPoints.append(point)
                
        return subPoints
    
    # Gets a list of x coordinates and a list of y coordinates from a list of point coordinates
    def getXY(self, points):
        
        x = []
        y = []
        
        for point in points:
            
            x.append(point[0])
            y.append(point[1])
        
        return x, y
    
    # Gets the slope and the intercept of a line from a list of x coordinates and a list of y coordinates 
    def getSlopeAndIntercept(self, x, y):
        
        m = (((mean(x) * mean(y)) - mean(x * y)) / ((mean(x) * mean(x)) - mean(x * x)))
        b = mean(y) - m * mean(x)
        
        return m, b


# Converts an Image object to an RGB Image object
def convertToRGB(img):
    
    img.load()
    
    rgb = Image.new("RGB", img.size, (255, 255, 255))
    rgb.paste(img, mask=img.split()[3])
    
    return rgb


# Adjusts the level of an RGB Image object
def adjustLevel(img, minv=0, maxv=255, gamma=1.0):

    if img.mode != "RGB":
        
        raise ValueError("Image not in RGB mode")

    newImg = img.copy()

    leveller = Level(minv, maxv, gamma)
    levelled_data = [
        leveller.convertAndLevel(data)
        for data in img.getdata()]
    newImg.putdata(levelled_data)
    
    return newImg


# Converts the image to greyscale
def convertToGreyscale(img):
    
    return ImageEnhance.Contrast(img).enhance(50.0)


# Coverts the image to binary mode
def binarizeImg(img):
    
    return img.convert('1')


# Threshold Segmentation for test purposes
def thresholdSegmentation():
    
    image = matplotlib.pyplot.imread('1117_607.png')
    image.shape
    
    # matplotlib.pyplot.imshow(image)
    
    gray = rgb2gray(image)
    # matplotlib.pyplot.imshow(gray, cmap='gray')
    
    gray_r = gray.reshape(gray.shape[0] * gray.shape[1])
    
    for i in range(gray_r.shape[0]):
        
        if gray_r[i] > gray_r.mean():
            
            gray_r[i] = 1
            
        else:
            
            gray_r[i] = 0
            
    gray = gray_r.reshape(gray.shape[0], gray.shape[1])
    # matplotlib.pyplot.imshow(gray, cmap='gray')
    
    # matplotlib.pyplot.imshow(image)
    
    gray = rgb2gray(image)
    gray_r = gray.reshape(gray.shape[0] * gray.shape[1])
    
    for i in range(gray_r.shape[0]):
        
        if gray_r[i] > gray_r.mean():
            
            gray_r[i] = 3
            
        elif gray_r[i] > 0.5:
            
            gray_r[i] = 2
            
        elif gray_r[i] > 0.25:
            
            gray_r[i] = 1
            
        else:
            
            gray_r[i] = 0
            
    gray = gray_r.reshape(gray.shape[0], gray.shape[1])
    matplotlib.pyplot.imsave('test.png', gray, cmap='gray')
    
    # img = Image.fromarray(gray , 'L')
    # return img


# K-Means Segmentation for test purposes
def kMeansSegmentation():
    
    pic = matplotlib.pyplot.imread('1117_607.png') / 225  # dividing by 255 to bring the pixel values between 0 and 1
    # print(pic.shape)
    # matplotlib.pyplot.imshow(pic)
    
    pic_n = pic.reshape(pic.shape[0] * pic.shape[1], pic.shape[2])
    pic_n.shape
    
    kmeans = KMeans(n_clusters=5, random_state=0).fit(pic_n)
    pic2show = kmeans.cluster_centers_[kmeans.labels_]
    
    cluster_pic = pic2show.reshape(pic.shape[0], pic.shape[1], pic.shape[2])
    # matplotlib.pyplot.imshow(cluster_pic)
    
    matplotlib.pyplot.imsave('test.png', cluster_pic)
    
    # img = Image.fromarray(cluster_pic , 'L')
    # return img


# Filters clusters based on pixel density and represents each cluster with a single point (dot)
def filterClusters(img, thresh):
    
    # Initialize cluster count
    clusCount = 0
    row = len(img)
    col = len(img[0])
    
    for i in range(row):
        
        for j in range(col):
            
            # Check for white pixel
            if img[i][j] == 255:
                
                img[i][j] = 1
                
                # Initialize size of cluster as mutable object and set the minimum value to 1
                size = [1]
                size[0] = 1 
                # size.append(1)
                
                # Perform DFS
                dfsWithSize(i, j, img, row, col, size)
                
                # Only 
                if size[0] > thresh:
                    
                    img[i][j] = 255
                
                # Update cluster count
                clusCount += 1
    
    return img


# DFS search that keeps track of the size (i.e. pixel density)
def dfsWithSize(i, j, img, row, col, size):
    
    if(i < 0 or i >= row or j < 0 or j >= col):
        
        return
    
    if(img[i][j] == 0):
        
        return
    
    if(img[i][j] == 255):
        
        img[i][j] = 0
        size[0] += 1
    
    dfsWithSize(i + 1, j, img, row, col, size)
    dfsWithSize(i, j + 1, img, row, col, size)
    dfsWithSize(i - 1, j, img, row, col, size)
    dfsWithSize(i, j - 1, img, row, col, size)


# Processes all images in an image list
def bulkProcess(imageList):
    
    processedImageList = []
    
    for i, img in enumerate(imageList):
        
        # Convert image to RGB
        rgb = convertToRGB(img)
        
        # Adjust image level
        levelledImg = adjustLevel(rgb, 100, 255, 9.99)
        
        # Convert to greyscale
        grayImg = convertToGreyscale(levelledImg)
        
        # Binarize image
        binImg = binarizeImg(grayImg)
        
        # Initialize trimmer
        trimmer = Trim(0.1, 1)
        
        # Trim image (Naive)
        trimmedImg = trimmer.smartTrim(binImg)
        
        # Update processed image list
        processedImageList.append(trimmedImg)
        
        # Display status
        print("Image {:03d}.png processing completed".format(i))
    
    return processedImageList


# Filters clusters in all images in an image list
def bulkFilter(imageList):
    
    filteredImageList = []
    
    for i, img in enumerate(imageList):
        
        # Filter clusters by pixel density and dot representation
        filteredImg = filterClusters(img, 10)
        
        # Update filtered image list
        filteredImageList.append(filteredImg)
        
        # Display status
        print("Image {:03d}.png cluster filtering completed".format(i))
        
    return filteredImageList


# Main function
def main():
    
    # Specify mode of operation and algorithm here
    batchMode = False
    lineFitAlg = "plotlib"
    
    if (not batchMode):
        
        filename = "filtered_images/037.png"
        
        line = Line()
        img = None
        
        # Open a single image
        try:
            
            img = imread(filename)
            
        except FileNotFoundError:
            
            print ("Invalid filename")
        
        # Image properties
        height = len(img)
        width = len(img[0])
        
        stripWidth = round(width / ROWS)
        
        points = line.getPoints(img)
        
        if lineFitAlg == "best" or lineFitAlg == "overlap":
            
            # Execute best fit algorithm
            segments = []
            
            for i in range(ROWS):
                
                subPoints = line.getSubPoints(points, i * stripWidth, (i + 1) * stripWidth)
                segments.append(line.getBestFit(subPoints, i * stripWidth, (i + 1) * stripWidth, height))
                
        if lineFitAlg == "strict" or lineFitAlg == "overlap":
            
            # Execute strict fit algorithm
            strictSegments = []
            
            strictBounds = line.getStrictFit(points, ROWS, height, width)
            lineGap = (strictBounds[1] - strictBounds[0]) / (ROWS - 1)
            
            for i in range(ROWS):
                
                strictSegments.append([(0, strictBounds[0] + (i * lineGap)), (height, strictBounds[0] + (i * lineGap))])
                
        if lineFitAlg == "plotlib" or lineFitAlg == "overlap":
        
            # Execute plotlib
            style.use('fivethirtyeight')
            
            # First strip for plot demonstration
            subPoints = line.getSubPoints(points, 0, stripWidth)
            
            x, y = line.getXY(subPoints)
            
            xs = numpy.array(x, dtype=numpy.float64)
            ys = numpy.array(y, dtype=numpy.float64)
            
            m, b = line.getSlopeAndIntercept(xs, ys)
            
            regLine = [(m * i) + b for i in xs]
            
            matplotlib.pyplot.scatter(xs, ys)
            matplotlib.pyplot.plot(xs, regLine)
            matplotlib.pyplot.show()
        
        # Definitions for pygame
        scaleFactor = 3
        
        window_height = height * scaleFactor
        window_width = width * scaleFactor
        
        clock_tick_rate = 20
        
        size = (window_width, window_height)
        screen = pygame.display.set_mode(size)
        
        pygame.display.set_caption("Best Fit Line")
        
        dead = False
        
        # Set pygame background
        clock = pygame.time.Clock()
        background_image = pygame.image.load(filename).convert()
        background_image = pygame.transform.scale(background_image, (window_width, window_height))
        
        while(dead == False):
            
            for event in pygame.event.get():
                
                if event.type == pygame.QUIT:
                    
                    dead = True
        
            screen.blit(background_image, [0, 0])
            
            # Check mode of operation
            if lineFitAlg == "best" or lineFitAlg == "overlap":
            
                for segment in segments:
                    
                    pygame.draw.lines(screen, (255, 0, 0), False, [(segment[0][1] * scaleFactor, segment[0][0] * scaleFactor), (segment[1][1] * scaleFactor, segment[1][0] * scaleFactor)], scaleFactor)
                
            if lineFitAlg == "strict" or lineFitAlg == "overlap":
            
                for strictSegment in strictSegments:
                    
                    pygame.draw.lines(screen, (255, 255, 0), False, [(strictSegment[0][1] * scaleFactor, strictSegment[0][0] * scaleFactor), (strictSegment[1][1] * scaleFactor, strictSegment[1][0] * scaleFactor)], scaleFactor)
            
            # Update and display
            pygame.display.update()
            pygame.display.flip()
            clock.tick(clock_tick_rate)
            
    else:
    
        # Initialize process handler
        handlerProcess = File(INPUTFOLDERNAME, INTERMEDFOLDERNAME)
        
        # Get images
        imageList = handlerProcess.getImages()
        
        # Process images
        processedImageList = bulkProcess(imageList)
        
        # Save images
        handlerProcess.setImages(processedImageList)
        
        # Initialize filter handler
        handlerFilter = File(INTERMEDFOLDERNAME, OUTPUTFOLDERNAME)
        
        # Get images
        imageList = handlerFilter.getSKImages()
        
        # Cluster filter images
        filteredImageList = bulkFilter(imageList)
        
        # Save images
        handlerFilter.setSKImages(filteredImageList)
    
    print("Program successfully terminated")
    return


if __name__ == '__main__':
    
    main()
    pass

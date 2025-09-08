#%%
import os
import sys
import comtypes # pip install comtypes
import comtypes.client
import numpy as np
from pathlib import Path
from utils import SafeArrayToNumpy
from utils import FrameTo3dArray
from utils import TypeLibFromObject
from nhdr_header import generate_nhdr_header
from pydicom import dcmread # NOTE: pydicom version 3.0 or above won't work. pip install "pydicom<3.0"
import matplotlib.pyplot as plt # pip install matplotlib
import matplotlib.animation as animation
import cv2 # OpenCV. for creating a movie. pip install opencv-python

# ------------------------------------------------------------
# for debugging use
# check if two .npy files are equal
do_flag = 0
if do_flag == 1:
    # to go the directory of this python code file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(script_dir)

    # load the .npy files
    array1 = np.load('P6NCEBO0 all beats.npy') # put the .npy file in the same directory of this python code file
    array2 = np.load('P6NER2G6 pac r2r.npy') # put the .npy file in the same directory of this python code file

    # check if they are equal
    are_equal = np.array_equal(array1, array2)

    print("Are the .npy files equal?", are_equal)
# ------------------------------------------------------------
#%%
# ------------------------------------------------------------
# INSERT THE DICOMDIR FILE PATH
# NOTE: use "\\", becuase this runs in Windows
file_path = 'Z:\\GE ultrasound data, patient\\598862 PAC, clear image' + '\\DICOMDIR' # clear image
# file_path = 'Z:\\GE ultrasound data, patient\\196303 PVC' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\494400 20 seconds' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\559098 last beat' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\559098 PAC' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\598862 all beats' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\598862 Normal' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\598862 PAC_R2R' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\598862 selected 3 beats' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\598862 slected 1 beat' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\605660 multiple recordings' + '\\DICOMDIR'
# file_path = 'Z:\\GE ultrasound data, patient\\625157_BeatAFIB multiple recordings' + '\\DICOMDIR'

DICOMDIR_path = Path(file_path) 
# ------------------------------------------------------------

# load the DICOMDIR file, which stores info of each recording
dicomdir = dcmread(DICOMDIR_path)

all_image_record = []
for patient_record in dicomdir.patient_records:
    print("Patient ID:", patient_record.PatientID)
    print("Patient Name:", patient_record.PatientName)
    for study_record in patient_record.children:
        print("Study Date:", study_record.StudyDate)
        print("Study Description:", study_record.StudyDescription)
        for series_record in study_record.children:
            # print("Series Number:", series_record.SeriesNumber)
            # print("Modality:", series_record.Modality)
            for image_record in series_record.children:
                # dicom_file_path = Path(DICOMDIR_path).parent / Path(*image_record.ReferencedFileID)
                # dicom_file_name = image_record.ReferencedFileID[4]
                # size_bytes = os.path.getsize(dicom_file_path)
                # size_mb = size_bytes / 1024 / 1024
                # print("DICOM File Name: ", dicom_file_name, '. Size: ', f"{size_mb:.1f}", "MB. Image Type", image_record.ImageType[3])
                all_image_record.append(image_record)

# create loader object
loader = comtypes.client.CreateObject("GEHC_CARD_US.Image3dFileLoader")
Image3dAPI = TypeLibFromObject(loader)
loader = loader.QueryInterface(Image3dAPI.IImage3dFileLoader) # cast to IImage3dFileLoader interface

# load file
for image_record in all_image_record:
    if image_record.ImageType[3] == '0041': # the 4D recordings
        dicom_file_name = image_record.ReferencedFileID[4]
        print("DICOM File Name: " + dicom_file_name)

        dicom_file_path = Path(DICOMDIR_path).parent / Path(*image_record.ReferencedFileID)
        err_type, err_msg = loader.LoadFile(str(dicom_file_path).replace('\\', '\\\\')) # NOTE: must have "err_type, err_msg = " at the beginning
        source = loader.GetImageSource()

        # # retrieve probe info
        # probe = source.GetProbeInfo()
        # print("Probe name: "+probe.name)
        # print("Probe type: "+str(probe.type))

        # retrieve ECG info
        ecg = source.GetECG()
        samples = SafeArrayToNumpy(ecg.samples)
        
        delta_time = ecg.delta_time
        start_time = ecg.start_time
        end_time = start_time + (len(samples)-1)*delta_time
        
        trig_times = SafeArrayToNumpy(ecg.trig_times)
        # t = np.arange(ecg.start_time, end_time+delta_time, delta_time) # maybe due to numerical precision error, this will result in 1 more element than "samples"
        # t = np.arange(ecg.start_time, end_time, delta_time) # maybe due to numerical precision error, this will result in 1 less element than "sample"
        t = [start_time]
        temp = start_time
        trig_time_id = []
        t_id = 0
        i = 0
        while abs(temp - end_time) > delta_time/2: # simply "temp < end_time" will not always work
            temp = temp  + delta_time
            t.append(temp)

            if i < len(trig_times):
                if abs(temp - trig_times[i]) < delta_time: # cannot use if temp == trig_times[i], because they are not exactly the same
                    trig_time_id.append(t_id)
                    i = i + 1

            t_id = t_id + 1

        # sys.exit() # for debugging using Jupyter notebook

        # save ECG as a plot
        plt.clf()
        plt.plot(t,samples)
        for i in range(0,len(trig_time_id)):
            plt.scatter(trig_times[i], samples[trig_time_id[i]], color='red')
        # plt.show()
        save_to_folder = Path(DICOMDIR_path).parent / Path("converted\\")
        if not os.path.isdir(save_to_folder):
            os.makedirs(save_to_folder)
        
        file_path = os.path.join(save_to_folder, dicom_file_name)
        plt.savefig(file_path+'_ecg.jpg', format='jpg', dpi=300)

        # get bounding box
        bbox = source.GetBoundingBox() # in jupyter notebook, dir(bbox) will show what bbox has
        origin = [bbox.origin_x, bbox.origin_y, bbox.origin_z]
        dir1   = [bbox.dir1_x,   bbox.dir1_y,   bbox.dir1_z]
        dir2   = [bbox.dir2_x,   bbox.dir2_y,   bbox.dir2_z]
        dir3   = [bbox.dir3_x,   bbox.dir3_y,   bbox.dir3_z]
        # print(origin)
        # print(dir1)
        # print(dir2)
        # print(dir3)

        # color_map = source.GetColorMap()
        # print("Color-map length: "+str(len(color_map)))

        # uuid = source.GetSopInstanceUID()

        frame_count = source.GetFrameCount()
        volumes = []
        volume_timings = []
        for i in range(frame_count):
            max_res = np.ctypeslib.as_ctypes(np.array([128, 128, 128], dtype=np.ushort)) 
            # [128, 128, 128]: the exported .npy will be about 50 MB, but image quality is not very good, segmentation can be difficult
            # [256, 256, 256]: the exported .npy will be about 500 MB, and image quality is much better. but will be a lot of work when doing the segmentation
            # [512, 512, 512]: the exported .npy will be about 4 GB, but no improvement in image quality
            frame = source.GetFrame(i, bbox, max_res)
            print("  Time stamps of 4D ultrasound recording: " + str(frame.time))

            data = FrameTo3dArray(frame)
            volumes.append(data)
            volume_timings.append(frame.time)

        # save the 4d numpy array
        if not os.path.isdir(save_to_folder):
            os.makedirs(save_to_folder)

        volumes = np.array(volumes)
        file_path = os.path.join(save_to_folder, dicom_file_name)
        np.save(file_path + ".npy", volumes)

        # generate the header file for the 4d numpy array
        # metadata = []
        metadata = f""" DOCSTRING 
# bouding box origin: {origin}
# bounding box axis 1: {dir1}
# bounding box axis 2: {dir2}
# bounding box axis 3: {dir3}"""
        generate_nhdr_header(Path(file_path + ".npy"), title=file_path, extrafields=metadata)

        # generate a cross section movie
        frame_count = volumes.shape[0]
        height, width = volumes.shape[2], volumes.shape[3] 
        
        video_writer = cv2.VideoWriter(file_path + ".mp4", 
                        cv2.VideoWriter_fourcc(*'mp4v'), # 'mp4v' is a common codec for .mp4 files
                        10,  # frames per second
                        (width, height),
                        isColor=False)  # Grayscale video

        for i in range(frame_count):
            frame = volumes[i, :, 64, :] # grab a slice
            video_writer.write(frame) # OpenCV expects (width, height), no transpose needed here because shape is (height, width)

        video_writer.release()

print("Done")
# %%

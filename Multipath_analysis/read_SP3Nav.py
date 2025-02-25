def readSP3Nav(filename, desiredGNSSsystems=None):
       
   import numpy as np
   import copy
   """
    Function that reads the GNSS satellite position data from a SP3 position
    #file. The function has been tested with sp3c and sp3d. NOTE: It is
    #advised that any use of this function is made through the parent function
    #"read_multiple_SP3Nav.m", as it has more functionality. 
    #--------------------------------------------------------------------------------------------------------------------------
    #INPUTS
    
    #filename:             path and filename of sp3 position file, string
    
    #desiredGNSSsystems:   array. Contains string. Each string is a code for a
    #                      GNSS system that should have its position data stored 
    #                      in sat_positions. Must be one of: "G", "R", "E",
    #                      "C". If left undefined, it is automatically set to
    #                      ["G", "R", "E", "C"]
    #--------------------------------------------------------------------------------------------------------------------------
    #OUTPUTS
    
    #sat_positions:    cell. Each cell elements contains position data for a
    #                  specific GNSS system. Order is defined by order of 
    #                  navGNSSsystems. Each cell element is another cell that 
    #                  stores position data of specific satellites of that 
    #                  GNSS system. Each of these cell elements is a matrix 
    #                  with [X, Y, Z] position of a epoch in each row.
    
    #                  sat_positions{GNSSsystemIndex}{PRN}(epoch, :) = [X, Y, Z]
    
    #epoch_dates:      matrix. Each row contains date of one of the epochs. 
    #                  [nEpochs x 6]
    
    #navGNSSsystems:   array. Contains string. Each string is a code for a
    #                  GNSS system with position data stored in sat_positions.
    #                  Must be one of: "G", "R", "E", "C"
    
    #nEpochs:          number of position epochs, integer
    
    #epochInterval:    interval of position epochs, seconds
    
    #success:          boolean, 1 if no error occurs, 0 otherwise
    #--------------------------------------------------------------------------------------------------------------------------

   #Function that reads the GNSS satellite position data from a SP3 position
   #file. The function has been tested with sp3c and sp3d. NOTE: It is
   #advised that any use of this function is made through the parent function
   #"read_multiple_SP3Nav.m", as it has more functionality. 
   #--------------------------------------------------------------------------------------------------------------------------
   #INPUTS

   #filename:             path and filename of sp3 position file, string

   #desiredGNSSsystems:   array. Contains string. Each string is a code for a
   #                      GNSS system that should have its position data stored 
   #                      in sat_positions. Must be one of: "G", "R", "E",
   #                      "C". If left undefined, it is automatically set to
   #                      ["G", "R", "E", "C"]
   #--------------------------------------------------------------------------------------------------------------------------
   #OUTPUTS

   #sat_positions:    cell. Each cell elements contains position data for a
   #                  specific GNSS system. Order is defined by order of 
   #                  navGNSSsystems. Each cell element is another cell that 
   #                  stores position data of specific satellites of that 
   #                  GNSS system. Each of these cell elements is a matrix 
   #                  with [X, Y, Z] position of a epoch in each row.

   #                  sat_positions{GNSSsystemIndex}{PRN}(epoch, :) = [X, Y, Z]

   #epoch_dates:      matrix. Each row contains date of one of the epochs. 
   #                  [nEpochs x 6]

   #navGNSSsystems:   array. Contains string. Each string is a code for a
   #                  GNSS system with position data stored in sat_positions.
   #                  Must be one of: "G", "R", "E", "C"

   #nEpochs:          number of position epochs, integer

   #epochInterval:    interval of position epochs, seconds

   #success:          boolean, 1 if no error occurs, 0 otherwise
   #--------------------------------------------------------------------------------------------------------------------------
   """


   #
   max_GNSSsystems = 4

   max_GPS_PRN     = 36 #Max number of GPS PRN in constellation
   max_GLONASS_PRN = 36 #Max number of GLONASS PRN in constellation
   max_Galileo_PRN = 36 #Max number of Galileo PRN in constellation
   max_Beidou_PRN  = 60 #Max number of BeiDou PRN in constellation
   max_sat = [max_GPS_PRN, max_GLONASS_PRN, max_Galileo_PRN, max_Beidou_PRN]

   #Initialize variables
   success = 1

   ## --- Open nav file

   try:
       fid = open(filename,'r')
   except:
       success = 0
       raise ValueError('No file selected!')
       
   if desiredGNSSsystems is None:
       desiredGNSSsystems = ["G", "R", "E", "C"]

   #GNSS system order
   navGNSSsystems = ["G", "R", "E", "C"];
   #Map mapping GNSS system code to GNSS system index
   # GNSSsystem_map = containers.Map(navGNSSsystems, [1, 2, 3, 4]);
   GNSSsystem_map = dict(zip(navGNSSsystems,[1, 2, 3, 4]))

   sat_pos = {}

   # Read header
   headerLine = 0
   line = fid.readline().rstrip()

   # All header lines begin with '*'
   while '*' not in line[0]:
       headerLine = headerLine + 1
       
       if headerLine == 1:
          sp3Version = line[0:2]
          
          # Control sp3 version    
          if '#c' not in sp3Version and '#d' not in sp3Version:
              print('ERROR(readSP3Nav): SP3 Navigation file is version %s, must be version c or d!' % (sp3Version))
              # [sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval] = deal(NaN)
              success = 0
              return success
        
          
          # Control that sp3 file is a position file and not a velocity file
          Pos_Vel_Flag = line[2]

          if 'P' not in Pos_Vel_Flag:
              print('ERROR(readSP3Nav): SP3 Navigation file is has velocity flag, should have position flag!')
              # [sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval] = deal(NaN);
              success = 0
              return success
          
          #Store coordinate system and amount of epochs
          CoordSys = line[46:51]
          nEpochs = int(line[32:39])
       
       
       if headerLine == 2:
          # Store GPS-week, "time-of-week" and epoch interval[seconds]
          GPS_Week = int(line[3:7])
          tow      = float(line[8:23])
          epochInterval = float(line[24:38])

       
       if headerLine == 3:
          
          #initialize list for storing indices of satellites to be excluded
          RemovedSatIndex = []
          
          
          if '#c' in sp3Version:
           nSat = int(line[4:6])
          else:
           nSat = int(line[3:6])
          
          ## -- Remove beginning of line
          line = line[9:60]
          
          #Initialize array for storing the order of satellites in the SP3
          #file(ie. what PRN and GNSS system index)
          
          GNSSsystemIndexOrder = []
          PRNOrder = []
           
          
          # Keep reading lines until all satellite IDs have been read
          for k in range(0,nSat):          
             # Control that current satellite is amoung desired systems
             if np.in1d(line[0], desiredGNSSsystems):
                
                 ## -- Get GNSSsystemIndex from map container
                 GNSSsystemIndex = GNSSsystem_map[line[0]]
                 #Get PRN number/slot number
                 PRN = int(line[1:3])
                 #remove satellite that has been read from line
                 line = line[3::]
                 #Store GNSSsystemIndex and PRN in satellite order arrays
                 GNSSsystemIndexOrder.append(GNSSsystemIndex)
                 PRNOrder.append(PRN)
                 
                 #if current satellite ID was last of a line, read next line
                 #and increment number of headerlines
                 if np.mod(k+1,17)==0 and k != 0: # FEILEN ER HER. DERFOR BLIR IKKE PR5 satellitten med
                     line = fid.readline().rstrip()
                     line = line[9:60]
                     headerLine = headerLine + 1
             #If current satellite ID is not amoung desired GNSS systems,
             #append its index to array of undesired satellites
             else:
                 RemovedSatIndex.append(k)
                 GNSSsystemIndexOrder.append(np.nan)
                 PRNOrder.append(np.nan)
                 
                 #if current satellite ID was last of a line, read next line
                 #and increment number of headerlines
                 if np.mod(k+1,17)==0 and k != 0: 
                     line = fid.readline().rstrip()
                     line = line[9:60]
                     headerLine = headerLine + 1;
       # Read next line
       line = fid.readline().rstrip()

   # Initialize matrix for epoch dates
   epoch_dates = []
   test = []
   sys_dict = {}
   PRN_dict = {}

   PRN_dict_GPS = {}
   PRN_dict_Glonass = {}
   PRN_dict_Galileo = {}
   PRN_dict_BeiDou = {}
   
   # Read satellite positions of every epoch    
   ini_sys = list(GNSSsystem_map.keys())[0]
   for k in range(0,nEpochs):
       #Store date of current epoch
       epochs = line[3:31].split(" ")       
       epochs = [x for x in epochs if x != "" ] # removing ''
       ## -- Make a check if theres a new line. (if hearder not giving correct nepochs)
       if epochs == []:
           print("The number of epochs given in the headers is not correct! \nInstead of %s epochs, the files contains %s epochs.\nSP3-file \"%s\" has been read successfully" %(str(nEpochs),str(k+1),filename))
           return sat_pos, epoch_dates, navGNSSsystems, nEpochs, epochInterval,success
       epoch_dates.append(epochs)
       
       # Store positions of all satellites for current epoch
       obs_dict = {}
       obs_dict_GPS = {}
       obs_dict_Glonass = {}
       obs_dict_Galileo = {}
       obs_dict_BeiDou = {}
       
       for i in range(0,nSat):
           #read next line
           line = fid.readline().rstrip()
           #if current satellite is amoung desired systems, store positions
           if np.in1d(i, RemovedSatIndex,invert = True):
               #Get PRN and GNSSsystemIndex of current satellite for
               #previously stored order
               PRN = PRNOrder[i]
               GNSSsystemIndex = GNSSsystemIndexOrder[i]
               # Store position of current satellite in correct location in
               sys_keys = list(GNSSsystem_map.keys())
               sys_values = list(GNSSsystem_map.values())
               sys_inx = sys_values.index(GNSSsystemIndex)
               sys = sys_keys[sys_inx]
               obs = line[5:46].split(" ")
               obs = [float(x)*1000 for x in obs if x != "" ] # multipliing with 1000 to get meters
              
               
               if sys != ini_sys:
                   ini_sys = sys

               # obs_dict[str(PRN)]  = obs[:]
               
               # obs_dict[str(PRN)]  = np.array([obs]) 
               # PRN_dict[int(k)] = obs_dict
               
               
               if sys == 'G':
                   obs_G = [x for x in obs if x != "" ]
                   # obs_dict_GPS[PRN]  = obs_G.copy()
                   # PRN_dict_GPS[k] = obs_dict.copy()

                   # test.append(obs_G[:])
                   # obs_dict_GPS[PRN]  = test[:][:]
                   
                   # obs_dict_GPS[PRN]  = np.array([obs_G])
                   # PRN_dict_GPS[k] = obs_dict_GPS
                   
                   obs_dict_GPS[PRN]  = np.array([obs_G])
                   PRN_dict_GPS[k] = obs_dict_GPS
               elif sys =='R':
                   obs_R = [x for x in obs if x != "" ]
                   # obs_dict_Glonass[PRN]  = obs_R.copy()
                   # PRN_dict_Glonass[k] = obs_dict_Glonass.copy()
                   obs_dict_Glonass[PRN]  = np.array([obs_R])
                   PRN_dict_Glonass[k] = obs_dict_Glonass
               elif sys =='E':
                   obs_E = [x for x in obs if x != "" ]
                   # obs_dict_Galileo[PRN]  = obs_E.copy()
                   # PRN_dict_Galileo[k] = obs_dict_Galileo.copy()
                   obs_dict_Galileo[PRN]  = np.array([obs_E])
                   PRN_dict_Galileo[k] = obs_dict_Galileo
               elif sys =='C':
                   obs_C = [x for x in obs if x != "" ]
                   # obs_dict_BeiDou[PRN]  = obs_C.copy()
                   # PRN_dict_BeiDou[k] = obs_dict_BeiDou.copy()
                   obs_dict_BeiDou[PRN]  = np.array([obs_C])
                   PRN_dict_BeiDou[k] = obs_dict_BeiDou
                   
           # sys_dict['G'] = obs_dict_GPS       
           sys_dict['G'] = PRN_dict_GPS
           sys_dict['R'] = PRN_dict_Glonass
           sys_dict['E'] = PRN_dict_Galileo
           sys_dict['C'] = PRN_dict_BeiDou
           sat_pos[sys] = sys_dict[sys]
                   
       #Get next line
       line = fid.readline().rstrip()
       
   #the next line should be eof. If not, raise warning
   try:
       line = fid.readline().rstrip()
   except:
       print('ERROR(readSP3Nav): End of file was not reached when expected!!')
       success = 0
       return success
        
   #remove NaN values
   GNSSsystemIndexOrder = [x for x in GNSSsystemIndexOrder if x != 'nan']
   PRNOrder = [x for x in GNSSsystemIndexOrder if x != 'nan']
   epoch_dates = np.array(epoch_dates) # Added this 27.11.2022 (to make it possible to use only one file i Multipath analysis!)

   print('SP3 Navigation file "%s" has been read successfully.' %(filename))
   ## Remove GNSS systems not present in navigation file
   # sat_pos['GNSS_systems']  = sat_pos['GNSS_systems'][np.unique(GNSSsystemIndexOrder)]
   # navGNSSsystems = navGNSSsystems(np.unique(GNSSsystemIndexOrder))
   return sat_pos, epoch_dates, navGNSSsystems, nEpochs, epochInterval,success

def combineSP3Nav(three_sp3_files,sat_positions_1, epoch_dates_1, navGNSSsystems_1, \
                  nEpochs_1, epochInterval_1,sat_positions_2, epoch_dates_2, navGNSSsystems_2,\
                  nEpochs_2, epochInterval_2, sat_positions_3, epoch_dates_3, navGNSSsystems_3,\
                  nEpochs_3, epochInterval_3,GNSSsystems):
    
    """
    # Function that combines the precise orbital data of two or three SP3
    # files. Note that the SP3 files should first be read by the function
    # readSP3Nav.m. 
    #--------------------------------------------------------------------------------------------------------------------------
    # INPUTS:
    
    # three_sp3_files:      boolean. 1 if there are three SP3 files to be
    #                       combined, 0 otherwise
    
    # sat_positions_1:      cell. Conatains data from first SP3 file. Each cell 
    #                       elements contains position data for a specific GNSS 
    #                       system. Order is defined by order of navGNSSsystems_1. 
    #                       Each cell element is another cell that stores 
    #                       position data of specific satellites of that 
    #                       GNSS system. Each of these cell elements is a matrix 
    #                       with [X, Y, Z] position of a epoch in each row.
    
    #                       sat_positions_1{GNSSsystemIndex}{PRN}(epoch, :) = [X, Y, Z]
    
    # epoch_dates_1:        matrix. Each row contains date of one of the epochs 
    #                       from the first SP3 file
    #                       [nEpochs_1 x 6]
    
    # navGNSSsystems_1:     array. Contains string. Each string is a code for a
    #                       GNSS system with position data stored in sat_positions.
    #                       Must be one of: "G", "R", "E", "C"
    
    # nEpochs_1:            number of position epochs in first SP3 file, integer
    
    # epochInterval_1:      interval of position epochs in first SP3 file, seconds
    
    # sat_positions_2:      cell. Conatains data from second SP3 file. Each cell 
    #                       elements contains position data for a specific GNSS 
    #                       system. Order is defined by order of navGNSSsystems_2. 
    #                       Each cell element is another cell that stores 
    #                       position data of specific satellites of that 
    #                       GNSS system. Each of these cell elements is a matrix 
    #                       with [X, Y, Z] position of a epoch in each row.
    
    #                       sat_positions_2{GNSSsystemIndex}{PRN}(epoch, :) = [X, Y, Z]
    
    # epoch_dates_2:        matrix. Each row contains date of one of the epochs 
    #                       from the second SP3 file
    #                       [nEpochs_1 x 6]
    
    # navGNSSsystems_2:     array. Contains string. Each string is a code for a
    #                       GNSS system with position data stored in sat_positions.
    #                       Must be one of: "G", "R", "E", "C"
    
    # nEpochs_2:            number of position epochs in first SP3 file, integer
    
    # epochInterval_2:      interval of position epochs in second SP3 file, seconds
    
    # sat_positions_3:      cell. Conatains data from third SP3 file. Each cell 
    #                       elements contains position data for a specific GNSS 
    #                       system. Order is defined by order of navGNSSsystems_3. 
    #                       Each cell element is another cell that stores 
    #                       position data of specific satellites of that 
    #                       GNSS system. Each of these cell elements is a matrix 
    #                       with [X, Y, Z] position of a epoch in each row.
    
    #                       sat_positions_3{GNSSsystemIndex}{PRN}(epoch, :) = [X, Y, Z]
    
    # epoch_dates_3:        matrix. Each row contains date of one of the epochs 
    #                       from the third SP3 file
    #                       [nEpochs_1 x 6]
    
    # navGNSSsystems_3 :    array. Contains string. Each string is a code for a
    #                       GNSS system with position data stored in sat_positions.
    #                       Must be one of: "G", "R", "E", "C"
    
    # nEpochs_3:            number of position epochs in third SP3 file, integer
    
    # epochInterval_3:      interval of position epochs in third SP3 file, seconds
    #--------------------------------------------------------------------------------------------------------------------------
    # OUTPUTS:
    
    # sat_positions:        cell. Conatains data from all two/three SP3 file. Each cell 
    #                       elements contains position data for a specific GNSS 
    #                       system. Order is defined by order of navGNSSsystems_1. 
    #                       Each cell element is another cell that stores 
    #                       position data of specific satellites of that 
    #                       GNSS system. Each of these cell elements is a matrix 
    #                       with [X, Y, Z] position of a epoch in each row.
    
    # epoch_dates:          matrix. Each row contains date of one of the epochs 
    #                       from all two/three SP3 file
    #                       [nEpochs_1 x 6]
    
    # navGNSSsystems:       array. Contains string. Each string is a code for a
    #                       GNSS system with position data stored in sat_positions.
    #                       Must be one of: "G", "R", "E", "C"
    
    # nEpochs:              number of position epochs in all two/three SP3 file, integer
    
    # epochInterval:        interval of position epochs in all SP3 file, seconds
    
    
    # success:              boolean, 1 if no error occurs, 0 otherwise
    #--------------------------------------------------------------------------------------------------------------------------
    
    """
    
    import numpy as np
    import copy 
    
    success = 1 # Setting success to 1 
    
    ## -- Check that first two SP3 files have same interval
    if epochInterval_1 != epochInterval_2:
        print('ERROR(combineSP3Nav):The first and second SP3 files do not have the same epoch interval') 
        sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval = np.nan,np.nan,np.nan,np.nan,np.nan
        success = 0
        return success
    
    
    ## -- Check that first two SP3 files have same GNSS systems
    # if ~isempty(setdiff(navGNSSsystems_1, navGNSSsystems_2)):
    if list(set(navGNSSsystems_1) - set(navGNSSsystems_2)):
        print('ERROR(CombineSP3Nav): SP3 file 1 and 2 do not contain the same GNSS systems')
        sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval = np.nan,np.nan,np.nan,np.nan,np.nan
        success = 0
        return success
    
    
    if three_sp3_files:
        ## -- Check that last SP3 file has same GNSS systems as the others
        if list(set(navGNSSsystems_2) - set(navGNSSsystems_3)):
            print('ERROR(CombineSP3Nav): SP3 file 3 does not contain the same GNSS systems as SP3 file 1 and 2')
            sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval = np.nan,np.nan,np.nan,np.nan,np.nan
            success = 0
            return success

    
    
    
    nGNSSsystems = len(navGNSSsystems_1)
    max_GPS_PRN     = 36 # Max number of GPS PRN in constellation
    max_GLONASS_PRN = 36 # Max number of GLONASS PRN in constellation
    max_Galileo_PRN = 36 # Max number of Galileo PRN in constellation
    max_Beidou_PRN  = 60 # Max number of BeiDou PRN in constellation
    max_sat = np.array([max_GPS_PRN, max_GLONASS_PRN, max_Galileo_PRN, max_Beidou_PRN])
    
    navGNSSsystems = navGNSSsystems_1
    epochInterval = epochInterval_1
    
    ## -- Combine epoch dates from first and second SP3 file
    epoch_dates = np.vstack([epoch_dates_1,epoch_dates_2])  
    
    ## -- Compute total amount of epochs
    nEpochs = nEpochs_1 + nEpochs_2
    
    ## -- Initialize cell structure for storing combined satellite positions
    sat_positions = copy.deepcopy(sat_positions_1)
    
    # Combine satellite positions from first and second SP3 file
    # for k in range(0,nGNSSsystems):
    for k in range(0,len(GNSSsystems)): ## added 07.01.2023 len(GNSSsystems) to prevent problem when running analysis on one system only
       curr_sys = GNSSsystems[k+1]
       len_sat = len(sat_positions_1[curr_sys])
       for ep in range(0,len(sat_positions_2[curr_sys].keys())):
           sat_positions[curr_sys].update({ep+len_sat: sat_positions_2[curr_sys][ep]})
       
    
    # If three SP3 files are present
    if three_sp3_files:
        # Add epoch dates from thirs SP3 file to the first two 
        epoch_dates = np.vstack([epoch_dates, epoch_dates_3])
        # Compute total amount of epochs
        nEpochs = nEpochs + nEpochs_3
        
        # check that last SP3 file has same interval as the others
        if epochInterval_2 != epochInterval_3:
            print('ERROR(combineSP3Nav):The second and third SP3 files do not have the same epoch interval') 
            sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval = np.nan,np.nan,np.nan,np.nan,np.nan
            success = 0
            return success
        
        
        # check that last SP3 file has same GNSS systems as the others
        if list(set(navGNSSsystems_2) - set(navGNSSsystems_3)):
        # if ~isempty(setdiff(navGNSSsystems_2, navGNSSsystems_3))
            print('Warning (CombineSP3Nav): SP3 file 2 and 3 do not contain the same amount of GNSS systems') 
        
        
        # Combine satellite positions from first, second and third SP3 files           
        sat_positions_dum = copy.deepcopy(sat_positions)
        # for k in range(0,nGNSSsystems):
        for k in range(0,len(GNSSsystems)):  ## added 07.01.2023 len(GNSSsystems) to prevent problem when running analysis on one system only
           curr_sys = GNSSsystems[k+1]
           len_sat = len(sat_positions_dum[curr_sys])
           for ep in range(0,len(sat_positions_3[curr_sys].keys())):
               sat_positions[curr_sys].update({ep+len_sat: sat_positions_3[curr_sys][ep]})

    return sat_positions, epoch_dates, navGNSSsystems, nEpochs, epochInterval, success


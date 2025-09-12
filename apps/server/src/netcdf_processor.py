import netCDF4 as nc
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict

class NetCDFProcessor:
    @staticmethod
    def process_argo_file(file_path: str) -> List[Dict]:
        """Process ARGO NetCDF file and extract measurements using xarray"""
        try:
            # Load the NetCDF file using xarray
            ds = xr.open_dataset(file_path, decode_times=False)
            
            print(f"Available dimensions: {list(ds.dims.keys())}")
            print(f"Available variables: {list(ds.data_vars.keys())}")
            print(f"Available coordinates: {list(ds.coords.keys())}")
            
            measurements = []
            
            # Try to identify coordinate and data variables
            lat_vars = ['LATITUDE', 'latitude', 'lat', 'Latitude']
            lon_vars = ['LONGITUDE', 'longitude', 'lon', 'Longitude']
            time_vars = ['JULD', 'time', 'TIME', 'Time']
            pres_vars = ['PRES', 'pressure', 'PRESSURE', 'Pressure', 'depth', 'DEPTH']
            temp_vars = ['TEMP', 'temperature', 'TEMPERATURE', 'Temperature']
            sal_vars = ['PSAL', 'salinity', 'SALINITY', 'Salinity']
            
            # Find actual variable names
            lat_var = next((v for v in lat_vars if v in ds), None)
            lon_var = next((v for v in lon_vars if v in ds), None) 
            time_var = next((v for v in time_vars if v in ds), None)
            pres_var = next((v for v in pres_vars if v in ds), None)
            temp_var = next((v for v in temp_vars if v in ds), None)
            sal_var = next((v for v in sal_vars if v in ds), None)
            
            print(f"Found variables - lat: {lat_var}, lon: {lon_var}, time: {time_var}")
            print(f"Found variables - pres: {pres_var}, temp: {temp_var}, sal: {sal_var}")
            
            # Get data arrays
            lat_data = ds[lat_var] if lat_var else None
            lon_data = ds[lon_var] if lon_var else None
            time_data = ds[time_var] if time_var else None
            pres_data = ds[pres_var] if pres_var else None
            temp_data = ds[temp_var] if temp_var else None
            sal_data = ds[sal_var] if sal_var else None
            
            # Handle different data structures
            if pres_data is None or temp_data is None or sal_data is None:
                raise Exception("Missing required oceanographic data (pressure, temperature, or salinity)")
            
            # Convert to numpy arrays and handle dimensions
            if lat_data is not None:
                lat_array = lat_data.values
            else:
                lat_array = np.array([0.0])
                
            if lon_data is not None:
                lon_array = lon_data.values
            else:
                lon_array = np.array([0.0])
            
            if time_data is not None:
                try:
                    # Handle time data with proper reference date
                    time_values = time_data.values
                    
                    # Check for time units
                    if hasattr(time_data, 'units'):
                        units = time_data.units
                        if 'days since' in units:
                            ref_date_str = units.split('days since ')[1].strip()
                            if ref_date_str.startswith('0000-01-01'):
                                # Use more reasonable reference date for problematic files
                                reference_date = datetime(1900, 1, 1)
                            else:
                                try:
                                    if 'UTC' in ref_date_str:
                                        ref_date_str = ref_date_str.replace(' UTC', '')
                                    reference_date = datetime.strptime(ref_date_str, '%Y-%m-%d %H:%M:%S')
                                except ValueError:
                                    reference_date = datetime(1950, 1, 1)
                            
                            # Convert days to datetime
                            time_array = np.array([reference_date + pd.Timedelta(days=float(val)) 
                                                 for val in time_values])
                        else:
                            time_array = pd.to_datetime(time_values, errors='coerce')
                    else:
                        time_array = pd.to_datetime(time_values, errors='coerce')
                except:
                    time_array = np.array([datetime.now()])
            else:
                time_array = np.array([datetime.now()])
            
            # Process the measurement data
            pres_array = pres_data.values
            temp_array = temp_data.values
            sal_array = sal_data.values
            
            # Handle different array shapes
            if pres_array.ndim == 1:
                # 1D arrays - single profile
                n_measurements = len(pres_array)
                for i in range(n_measurements):
                    try:
                        # Get coordinates
                        lat = float(lat_array[0] if len(lat_array) > 0 else 0.0)
                        lon = float(lon_array[0] if len(lon_array) > 0 else 0.0)
                        timestamp = time_array[0] if len(time_array) > 0 else datetime.now()
                        
                        # Get measurements
                        pressure = float(pres_array[i]) if not pd.isna(pres_array[i]) else None
                        temperature = float(temp_array[i]) if not pd.isna(temp_array[i]) else None  
                        salinity = float(sal_array[i]) if not pd.isna(sal_array[i]) else None
                        
                        # More lenient validation - keep more data for analysis
                        if (pressure is None or pressure < 0 or pressure > 12000):
                            continue
                        # Allow missing temperature or salinity but flag them
                        if temperature is not None and (temperature < -5 or temperature > 45):
                            continue
                        if salinity is not None and (salinity < 0 or salinity > 50):
                            continue
                        # Convert None to a reasonable default or keep None for analysis
                        if temperature is None:
                            temperature = 0.0  # Flag value for missing data
                        if salinity is None:
                            salinity = 0.0  # Flag value for missing data
                        
                        measurement = {
                            'float_id': f"FLOAT_000001",
                            'latitude': lat,
                            'longitude': lon,
                            'date': timestamp,
                            'depth': pressure,
                            'temperature': temperature,
                            'salinity': salinity,
                            'pressure': pressure
                        }
                        measurements.append(measurement)
                        
                    except (ValueError, IndexError) as e:
                        print(f"Error processing measurement {i}: {e}")
                        continue
                        
            elif pres_array.ndim == 2:
                # 2D arrays - multiple profiles
                n_profiles = pres_array.shape[0] 
                n_levels = pres_array.shape[1]
                
                for prof in range(n_profiles):
                    for level in range(n_levels):
                        try:
                            # Get coordinates
                            lat = float(lat_array[prof] if len(lat_array) > prof else lat_array[0])
                            lon = float(lon_array[prof] if len(lon_array) > prof else lon_array[0])
                            timestamp = time_array[prof] if len(time_array) > prof else time_array[0]
                            
                            # Get measurements
                            pressure = float(pres_array[prof, level]) if not pd.isna(pres_array[prof, level]) else None
                            temperature = float(temp_array[prof, level]) if not pd.isna(temp_array[prof, level]) else None
                            salinity = float(sal_array[prof, level]) if not pd.isna(sal_array[prof, level]) else None
                            
                            # More lenient validation - keep more data for analysis
                            if (pressure is None or pressure < 0 or pressure > 12000):
                                continue
                            # Allow missing temperature or salinity but flag them
                            if temperature is not None and (temperature < -5 or temperature > 45):
                                continue
                            if salinity is not None and (salinity < 0 or salinity > 50):
                                continue
                            # Convert None to a reasonable default or keep None for analysis
                            if temperature is None:
                                temperature = 0.0  # Flag value for missing data
                            if salinity is None:
                                salinity = 0.0  # Flag value for missing data
                            
                            measurement = {
                                'float_id': f"FLOAT_{prof:06d}",
                                'latitude': lat,
                                'longitude': lon,
                                'date': timestamp,
                                'depth': pressure,
                                'temperature': temperature,
                                'salinity': salinity,
                                'pressure': pressure
                            }
                            measurements.append(measurement)
                            
                        except (ValueError, IndexError) as e:
                            print(f"Error processing profile {prof}, level {level}: {e}")
                            continue
            
            ds.close()
            print(f"Successfully extracted {len(measurements)} measurements")
            return measurements
            
        except Exception as e:
            print(f"Error processing NetCDF file: {e}")
            raise Exception(f"NetCDF processing failed: {str(e)}")
    
    @staticmethod
    def validate_file(file_path: str) -> bool:
        """Validate if file is a proper NetCDF file using xarray"""
        try:
            ds = xr.open_dataset(file_path, decode_times=False)
            # Check if we can open it and it has some data variables
            has_data = len(ds.data_vars) > 0
            ds.close()
            return has_data
        except Exception as e:
            print(f"NetCDF validation failed: {e}")
            return False
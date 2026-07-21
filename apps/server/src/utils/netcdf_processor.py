import netCDF4 as nc
import xarray as xr
import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
import time

class NetCDFProcessor:
    @staticmethod
    def process_argo_file(file_path: str) -> List[Dict]:
        """Process ARGO NetCDF file with optimized performance for large files"""
        start_time = time.time()
        print(f"Starting optimized NetCDF processing: {file_path}")

        try:
            result = NetCDFProcessor._process_argo_file_optimized(file_path)
            processing_time = time.time() - start_time
            print(f"NetCDF processing completed in {processing_time:.2f} seconds, extracted {len(result)} measurements")
            return result
        except Exception as e:
            processing_time = time.time() - start_time
            print(f"NetCDF processing failed after {processing_time:.2f} seconds: {e}")
            raise

    @staticmethod
    def _process_argo_file_optimized(file_path: str) -> List[Dict]:
        """Optimized processing with vectorized operations and memory efficiency"""
        try:
            # Load dataset with chunking for memory efficiency
            ds = xr.open_dataset(file_path, decode_times=False, chunks={'obs': 1000})

            print(f"Available dimensions: {list(ds.dims.keys())}")
            print(f"Available variables: {list(ds.data_vars.keys())}")
            print(f"Available coordinates: {list(ds.coords.keys())}")

            # Try to identify coordinate and data variables
            lat_vars = ['LATITUDE', 'latitude', 'lat', 'Latitude']
            lon_vars = ['LONGITUDE', 'longitude', 'lon', 'Longitude']
            time_vars = ['JULD', 'time', 'TIME', 'Time']
            pres_vars = ['PRES', 'pres', 'pressure', 'PRESSURE', 'Pressure', 'depth', 'DEPTH']
            temp_vars = ['TEMP', 'temp', 'temperature', 'TEMPERATURE', 'Temperature']
            sal_vars = ['PSAL', 'psal', 'salinity', 'SALINITY', 'Salinity']
            # ARGO WMO float-ID variable names (real instrument identifiers)
            float_id_vars = ['PLATFORM_NUMBER', 'platform_number', 'FLOAT_SERIAL_NO',
                             'float_serial_no', 'WMO_ID', 'wmo_id']

            # Find actual variable names
            lat_var = next((v for v in lat_vars if v in ds), None)
            lon_var = next((v for v in lon_vars if v in ds), None)
            time_var = next((v for v in time_vars if v in ds), None)
            pres_var = next((v for v in pres_vars if v in ds), None)
            temp_var = next((v for v in temp_vars if v in ds), None)
            sal_var = next((v for v in sal_vars if v in ds), None)
            float_id_var = next((v for v in float_id_vars if v in ds), None)

            print(f"Found variables - lat: {lat_var}, lon: {lon_var}, time: {time_var}")
            print(f"Found variables - pres: {pres_var}, temp: {temp_var}, sal: {sal_var}")
            print(f"Found float-ID variable: {float_id_var}")

            # Get data arrays
            lat_data = ds[lat_var] if lat_var else None
            lon_data = ds[lon_var] if lon_var else None
            time_data = ds[time_var] if time_var else None
            pres_data = ds[pres_var] if pres_var else None
            temp_data = ds[temp_var] if temp_var else None
            sal_data = ds[sal_var] if sal_var else None
            float_id_data = ds[float_id_var] if float_id_var else None

            # Handle different data structures
            if pres_data is None or temp_data is None or sal_data is None:
                raise Exception("Missing required oceanographic data (pressure, temperature, or salinity)")

            # Process time data efficiently
            time_array = NetCDFProcessor._process_time_data(time_data)

            # Extract float IDs from dataset (real WMO identifiers)
            float_ids = NetCDFProcessor._extract_float_ids(float_id_data, lat_data)

            # Use vectorized operations for much better performance
            measurements = NetCDFProcessor._extract_measurements_vectorized(
                pres_data, temp_data, sal_data, lat_data, lon_data, time_array, float_ids
            )

            ds.close()
            return measurements

        except Exception as e:
            print(f"Error processing NetCDF file: {e}")
            raise Exception(f"NetCDF processing failed: {str(e)}")

    @staticmethod
    def _process_time_data(time_data):
        """Process time data efficiently"""
        if time_data is not None:
            try:
                time_values = time_data.values

                if hasattr(time_data, 'units'):
                    units = time_data.units
                    if 'days since' in units:
                        ref_date_str = units.split('days since ')[1].strip()
                        if ref_date_str.startswith('0000-01-01'):
                            reference_date = datetime(1900, 1, 1)
                        else:
                            try:
                                if 'UTC' in ref_date_str:
                                    ref_date_str = ref_date_str.replace(' UTC', '')
                                reference_date = datetime.strptime(ref_date_str, '%Y-%m-%d %H:%M:%S')
                            except ValueError:
                                reference_date = datetime(1950, 1, 1)

                        # Vectorized time conversion - FIXED: Handle NaN values in time data
                        time_array = np.array([reference_date + pd.Timedelta(days=float(val))
                                             for val in time_values if not pd.isna(val)])
                    else:
                        time_array = pd.to_datetime(time_values, errors='coerce').values
                else:
                    time_array = pd.to_datetime(time_values, errors='coerce').values
            except Exception as e:
                print(f"Time processing failed: {e}, using current time")
                time_array = np.array([datetime.now()])
        else:
            time_array = np.array([datetime.now()])

        return time_array

    @staticmethod
    def _extract_float_ids(float_id_data, lat_data) -> List[Optional[str]]:
        """
        Extract real WMO float IDs from the PLATFORM_NUMBER variable.

        PLATFORM_NUMBER is stored as a char array in ARGO files:
          - 1D (N_PROF,) → each element is one profile's ID
          - 2D (N_PROF, N_CHAR) → each row is a char-padded ID string
        Falls back to None when the variable is absent; callers replace None
        with a deterministic fallback derived from coordinates.
        """
        if float_id_data is None:
            return []

        try:
            raw = float_id_data.values  # numpy array

            if raw.ndim == 0:
                # Scalar – single float
                wmo = str(raw).strip()
                return [wmo if wmo else None]

            if raw.ndim == 1:
                # Each element may already be a string or a bytes/char value
                ids = []
                for elem in raw:
                    if hasattr(elem, 'decode'):
                        wmo = elem.decode('utf-8', errors='ignore').strip()
                    else:
                        wmo = str(elem).strip()
                    ids.append(wmo if wmo and wmo not in ('nan', '') else None)
                return ids

            if raw.ndim == 2:
                # (N_PROF, N_CHAR) – join characters per row
                ids = []
                for row in raw:
                    chars = []
                    for ch in row:
                        if hasattr(ch, 'decode'):
                            chars.append(ch.decode('utf-8', errors='ignore'))
                        else:
                            chars.append(str(ch))
                    wmo = ''.join(chars).strip()
                    ids.append(wmo if wmo and wmo not in ('nan', '') else None)
                return ids

        except Exception as e:
            print(f"Warning: Could not extract float IDs from PLATFORM_NUMBER: {e}")

        return []

    @staticmethod
    def _fallback_float_id(profile_index: int, lat: float, lon: float) -> str:
        """
        Generate a deterministic fallback float ID when PLATFORM_NUMBER is absent.
        Uses a short hash of lat/lon so re-ingesting the same file produces the
        same IDs (important for duplicate detection).
        """
        import hashlib
        coord_key = f"{lat:.4f}_{lon:.4f}"
        short_hash = hashlib.md5(coord_key.encode()).hexdigest()[:6].upper()
        return f"ARGO_{short_hash}_{profile_index:04d}"

    @staticmethod
    def _extract_measurements_vectorized(pres_data, temp_data, sal_data,
                                         lat_data, lon_data, time_array,
                                         float_ids: List[Optional[str]] = None) -> List[Dict]:
        """Vectorized extraction of measurements for optimal performance"""
        # Convert to numpy arrays
        pres_array = pres_data.values
        temp_array = temp_data.values
        sal_array = sal_data.values

        if pres_array.ndim == 1:
            # 1D arrays - single profile (vectorized processing)
            return NetCDFProcessor._process_1d_profile_vectorized(
                pres_array, temp_array, sal_array, lat_data, lon_data, time_array, float_ids
            )
        elif pres_array.ndim == 2:
            # 2D arrays - multiple profiles (vectorized processing)
            return NetCDFProcessor._process_2d_profiles_vectorized(
                pres_array, temp_array, sal_array, lat_data, lon_data, time_array, float_ids
            )
        else:
            raise Exception(f"Unsupported data dimensionality: {pres_array.ndim}")

    @staticmethod
    def _process_1d_profile_vectorized(pres_array, temp_array, sal_array,
                                        lat_data, lon_data, time_array,
                                        float_ids: List[Optional[str]] = None) -> List[Dict]:
        """Process 1D profile data using vectorized operations"""
        # Create coordinate arrays
        lat = float(lat_data.values[0] if len(lat_data.values) > 0 else 0.0)
        lon = float(lon_data.values[0] if len(lon_data.values) > 0 else 0.0)
        timestamp = time_array[0] if len(time_array) > 0 else datetime.now()

        # Resolve float ID: use real WMO ID (index 0 for 1D = single profile)
        # then fall back to a deterministic hash of coordinates
        if float_ids and len(float_ids) > 0 and float_ids[0]:
            float_id = float_ids[0]
        else:
            float_id = NetCDFProcessor._fallback_float_id(0, lat, lon)
        print(f"1D Profile: using float_id={float_id}")

        # Vectorized validation masks - FIXED: Only accept non-NaN valid data
        valid_pressure = (~pd.isna(pres_array)) & (pres_array >= 0) & (pres_array <= 12000)
        valid_temp = (~pd.isna(temp_array)) & (temp_array >= -5) & (temp_array <= 45)
        valid_sal = (~pd.isna(sal_array)) & (sal_array >= 0) & (sal_array <= 50)
        valid_mask = valid_pressure & valid_temp & valid_sal

        # Extract valid data using boolean indexing
        valid_indices = np.where(valid_mask)[0]

        print(f"1D Profile: Found {len(valid_indices)} valid measurements out of {len(pres_array)} total")

        # Vectorized data extraction - FIXED: No NaN conversion to 0.0
        valid_pressure_vals = pres_array[valid_indices].astype(float)
        valid_temp_vals = temp_array[valid_indices].astype(float)
        valid_sal_vals = sal_array[valid_indices].astype(float)

        # Create measurements in batch
        measurements = []
        for i in range(len(valid_indices)):
            measurements.append({
                'float_id': float_id,
                'latitude': lat,
                'longitude': lon,
                'date': timestamp,
                'depth': valid_pressure_vals[i],
                'temperature': valid_temp_vals[i],
                'salinity': valid_sal_vals[i],
                'pressure': valid_pressure_vals[i]
            })

        print(f"1D Profile: Created {len(measurements)} valid measurement records")
        return measurements

    @staticmethod
    def _process_2d_profiles_vectorized(pres_array, temp_array, sal_array,
                                         lat_data, lon_data, time_array,
                                         float_ids: List[Optional[str]] = None) -> List[Dict]:
        """Process 2D profile data using vectorized operations"""
        lat_array_vals = lat_data.values
        lon_array_vals = lon_data.values

        # Vectorized validation - FIXED: Only accept non-NaN valid data
        valid_pressure = (~pd.isna(pres_array)) & (pres_array >= 0) & (pres_array <= 12000)
        valid_temp = (~pd.isna(temp_array)) & (temp_array >= -5) & (temp_array <= 45)
        valid_sal = (~pd.isna(sal_array)) & (sal_array >= 0) & (sal_array <= 50)
        valid_mask = valid_pressure & valid_temp & valid_sal

        # Get valid indices
        prof_indices, level_indices = np.where(valid_mask)

        print(f"2D Profiles: Found {len(prof_indices)} valid measurements from {pres_array.shape} array shape")

        # Vectorized data extraction - FIXED: No NaN conversion to 0.0
        valid_pressure_vals = pres_array[prof_indices, level_indices].astype(float)
        valid_temp_vals = temp_array[prof_indices, level_indices].astype(float)
        valid_sal_vals = sal_array[prof_indices, level_indices].astype(float)

        # Create measurements in batch
        measurements = []
        for i in range(len(prof_indices)):
            prof = prof_indices[i]

            # Handle coordinate arrays
            lat = float(lat_array_vals[prof] if prof < len(lat_array_vals) else lat_array_vals[0])
            lon = float(lon_array_vals[prof] if prof < len(lon_array_vals) else lon_array_vals[0])
            timestamp = time_array[prof] if prof < len(time_array) else time_array[0]

            # Resolve real WMO float ID for this profile index
            if float_ids and prof < len(float_ids) and float_ids[prof]:
                float_id = float_ids[prof]
            else:
                float_id = NetCDFProcessor._fallback_float_id(int(prof), lat, lon)

            measurements.append({
                'float_id': float_id,
                'latitude': lat,
                'longitude': lon,
                'date': timestamp,
                'depth': valid_pressure_vals[i],
                'temperature': valid_temp_vals[i],
                'salinity': valid_sal_vals[i],
                'pressure': valid_pressure_vals[i]
            })

        print(f"2D Profiles: Created {len(measurements)} valid measurement records")
        return measurements

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
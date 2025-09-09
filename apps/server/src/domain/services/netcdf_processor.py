import netCDF4 as nc
import numpy as np
from datetime import datetime
from typing import List
from ..entities.argo_measurement import ArgoMeasurement

class NetCDFProcessor:
    @staticmethod
    def validate_file(file_path: str) -> bool:
        try:
            dataset = nc.Dataset(file_path, 'r')
            dataset.close()
            return True
        except:
            return False
    
    @staticmethod
    def extract_measurements(file_path: str) -> List[ArgoMeasurement]:
        try:
            dataset = nc.Dataset(file_path, 'r')
            measurements = []
            
            n_prof = len(dataset.dimensions['N_PROF'])
            n_levels = len(dataset.dimensions['N_LEVELS'])
            
            latitude = dataset.variables.get('LATITUDE', [])
            longitude = dataset.variables.get('LONGITUDE', [])
            juld = dataset.variables.get('JULD', [])
            pres = dataset.variables.get('PRES', [])
            temp = dataset.variables.get('TEMP', [])
            sal = dataset.variables.get('PSAL', [])
            
            reference_date = datetime(1950, 1, 1)
            
            for prof in range(n_prof):
                float_id = f"ARGO_{prof:06d}"
                
                try:
                    prof_lat = float(latitude[prof]) if len(latitude) > prof else 0.0
                    prof_lon = float(longitude[prof]) if len(longitude) > prof else 0.0
                    prof_date = reference_date if len(juld) == 0 else reference_date.replace(year=reference_date.year + int(juld[prof] // 365))
                except (IndexError, ValueError):
                    prof_lat = prof_lon = 0.0
                    prof_date = reference_date
                
                for level in range(min(n_levels, 50)):
                    try:
                        if len(pres.shape) == 2:
                            pressure = float(pres[prof, level]) if not np.ma.is_masked(pres[prof, level]) else None
                            temperature = float(temp[prof, level]) if not np.ma.is_masked(temp[prof, level]) else None
                            salinity = float(sal[prof, level]) if not np.ma.is_masked(sal[prof, level]) else None
                        else:
                            pressure = float(pres[level]) if level < len(pres) and not np.ma.is_masked(pres[level]) else None
                            temperature = float(temp[level]) if level < len(temp) and not np.ma.is_masked(temp[level]) else None
                            salinity = float(sal[level]) if level < len(sal) and not np.ma.is_masked(sal[level]) else None
                        
                        if not NetCDFProcessor._is_valid_measurement(pressure, temperature, salinity):
                            continue
                            
                        measurement = ArgoMeasurement(
                            float_id=float_id,
                            latitude=prof_lat,
                            longitude=prof_lon,
                            date=prof_date,
                            depth=pressure,
                            temperature=temperature,
                            salinity=salinity,
                            pressure=pressure
                        )
                        measurements.append(measurement)
                        
                    except (IndexError, ValueError, TypeError):
                        continue
            
            dataset.close()
            return measurements
            
        except Exception:
            return []
    
    @staticmethod
    def _is_valid_measurement(pressure: float, temperature: float, salinity: float) -> bool:
        if pressure is None or temperature is None or salinity is None:
            return False
        if pressure < 0 or temperature < -5 or temperature > 40 or salinity < 0 or salinity > 50:
            return False
        return True
# Test Data Directory

This directory contains test NetCDF files with realistic Indian Ocean ARGO float data for testing the FloatChat application.

## Test Files

### 1. `test_indian_argo.nc` (Original)
- **Region**: General Indian Ocean
- **Profiles**: 5 profiles, 20 depth levels each
- **Coordinates**: Various locations across the Indian Ocean
- **Characteristics**: Mixed oceanographic conditions representing typical Indian Ocean patterns

### 2. `test_bay_of_bengal_argo.nc` (New)
- **Region**: Bay of Bengal (Northeast Indian Ocean)
- **Profiles**: 6 profiles, 25 depth levels each
- **Coordinates**: 10°N-22°N, 80°E-95°E
- **Characteristics**:
  - Lower salinity (32.5-36.0 PSU) due to freshwater input from rivers (Ganges, Brahmaputra)
  - Higher surface temperatures (28-30.5°C)
  - Strong thermocline development
  - Monsoon-influenced oceanography

### 3. `test_arabian_sea_argo.nc` (New)
- **Region**: Arabian Sea (Northwest Indian Ocean)
- **Profiles**: 7 profiles, 22 depth levels each
- **Coordinates**: 5°N-25°N, 55°E-75°E
- **Characteristics**:
  - Higher salinity (35.5-36.8 PSU) due to high evaporation rates
  - Variable surface temperatures (25-29°C) due to upwelling
  - Strong oxygen minimum zones
  - Influenced by southwest monsoon upwelling

### 4. `test_southern_indian_ocean_argo.nc` (New)
- **Region**: Southern Indian Ocean (Subantarctic region)
- **Profiles**: 5 profiles, 30 depth levels each (deeper measurements)
- **Coordinates**: 30°S-45°S, 60°E-120°E
- **Characteristics**:
  - Cooler temperatures (14-18°C surface, down to 0.5°C at depth)
  - Moderate salinity (34.2-34.9 PSU)
  - Deep convection and water mass formation
  - Antarctic influence on water properties
  - Measurements down to 3000m depth

## Data Structure

All files follow the standard ARGO NetCDF format with the following variables:

- **LATITUDE**: Latitude of each profile (degrees_north)
- **LONGITUDE**: Longitude of each profile (degrees_east)
- **JULD**: Julian day (days since 1950-01-01 00:00:00 UTC)
- **PRES**: Sea pressure in decibars (roughly equivalent to depth in meters)
- **TEMP**: Sea temperature in degrees Celsius
- **PSAL**: Practical salinity (unitless, typically 32-37 for ocean water)

## Usage

These files can be used to test:

1. **File upload functionality** - Different file sizes and profile counts
2. **Data processing** - Various oceanographic conditions and data ranges
3. **Duplicate detection** - Different geographical regions to test similarity algorithms
4. **Search functionality** - Query different regions and data characteristics
5. **Visualization** - Display different oceanographic patterns

## Oceanographic Context

Each test file represents realistic oceanographic conditions:

- **Bay of Bengal**: Influenced by river discharge, creating a unique low-salinity environment
- **Arabian Sea**: Characterized by strong seasonal upwelling and high evaporation
- **Southern Indian Ocean**: Represents the transition to Antarctic waters with deep convection
- **General Indian Ocean**: Mixed conditions representing the broader basin

## Technical Notes

- All files use the NetCDF4 format
- Data types: float64 for coordinates/time, float32 for oceanographic measurements
- Realistic data ranges based on known oceanographic patterns
- Includes proper metadata and units following ARGO conventions
- Compatible with the existing NetCDF processor in the FloatChat application

## Regenerating Test Data

To regenerate or modify these test files, run the `generate_test_files.py` script from the project root:

```bash
python generate_test_files.py
```

This script creates realistic synthetic data based on known oceanographic patterns for each region.

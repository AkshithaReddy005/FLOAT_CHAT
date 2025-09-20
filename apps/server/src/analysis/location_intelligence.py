"""
Enhanced Location Intelligence for Oceanographic Data
Provides detailed geographic analysis and context for ARGO float measurements
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')

# Geospatial libraries
try:
    import reverse_geocoder as rg
    import pycountry
    from geopy.distance import great_circle
    from geographiclib.geodesic import Geodesic
    GEOSPATIAL_AVAILABLE = True
except ImportError:
    GEOSPATIAL_AVAILABLE = False

# Scientific libraries
from geopy.geocoders import Nominatim


@dataclass
class LocationContext:
    """Enhanced location context for oceanographic measurements"""
    coordinates: Tuple[float, float]  # (lat, lon)
    country: Optional[str] = None
    country_code: Optional[str] = None
    admin1: Optional[str] = None  # State/Province
    admin2: Optional[str] = None  # County/District
    ocean_basin: Optional[str] = None
    marine_region: Optional[str] = None
    eez_zone: Optional[str] = None  # Exclusive Economic Zone
    distance_to_coast: Optional[float] = None  # km
    depth_zone: Optional[str] = None
    oceanographic_region: Optional[str] = None
    circulation_feature: Optional[str] = None
    seasonal_characteristics: Optional[Dict] = None


@dataclass
class RegionalAnalysis:
    """Comprehensive regional analysis results"""
    region_name: str
    measurement_count: int
    float_count: int
    spatial_bounds: Dict[str, float]
    oceanographic_features: List[str]
    environmental_context: Dict[str, Any]
    statistical_summary: Dict[str, float]
    data_quality_metrics: Dict[str, float]


class LocationIntelligence:
    """Advanced geospatial intelligence for oceanographic data"""

    def __init__(self):
        self.geocoder = Nominatim(user_agent="oceanographic_intelligence", timeout=10)
        self.geod = Geodesic.WGS84 if GEOSPATIAL_AVAILABLE else None

        # Ocean basin definitions
        self.ocean_basins = {
            'Arabian Sea': {
                'bounds': {'lat_min': 0, 'lat_max': 30, 'lon_min': 50, 'lon_max': 80},
                'features': ['Monsoon circulation', 'Upwelling zones', 'Oxygen minimum zone']
            },
            'Bay of Bengal': {
                'bounds': {'lat_min': 5, 'lat_max': 25, 'lon_min': 80, 'lon_max': 100},
                'features': ['River discharge influence', 'Tropical cyclones', 'Stratification']
            },
            'Southern Indian Ocean': {
                'bounds': {'lat_min': -60, 'lat_max': -10, 'lon_min': 20, 'lon_max': 140},
                'features': ['Antarctic Circumpolar Current', 'Subantarctic waters', 'Deep water formation']
            },
            'Equatorial Indian Ocean': {
                'bounds': {'lat_min': -10, 'lat_max': 10, 'lon_min': 40, 'lon_max': 120},
                'features': ['Indian Ocean Dipole', 'Equatorial currents', 'Thermocline variability']
            },
            'Western Indian Ocean': {
                'bounds': {'lat_min': -40, 'lat_max': 30, 'lon_min': 20, 'lon_max': 70},
                'features': ['Agulhas Current', 'Somali Current', 'Coastal upwelling']
            }
        }

        # Marine protected areas and special regions
        self.special_regions = {
            'Coral Triangle': {
                'bounds': {'lat_min': -15, 'lat_max': 15, 'lon_min': 100, 'lon_max': 140},
                'significance': 'High biodiversity hotspot'
            },
            'Madagascar Ridge': {
                'bounds': {'lat_min': -35, 'lat_max': -10, 'lon_min': 40, 'lon_max': 60},
                'significance': 'Underwater mountain range'
            },
            'Mascarene Plateau': {
                'bounds': {'lat_min': -25, 'lat_max': -10, 'lon_min': 55, 'lon_max': 75},
                'significance': 'Volcanic hotspot region'
            }
        }

    def enhance_location_data(self, df: pd.DataFrame) -> pd.DataFrame:
        """Enhance DataFrame with detailed location intelligence"""
        if not GEOSPATIAL_AVAILABLE:
            print("Warning: Geospatial libraries not available, returning original dataframe")
            return df

        enhanced_df = df.copy()

        # Check for required columns
        if 'latitude' not in enhanced_df.columns or 'longitude' not in enhanced_df.columns:
            print("Warning: latitude/longitude columns not found, returning original dataframe")
            return enhanced_df

        # Add location context for each measurement
        location_contexts = []
        print(f"Processing {len(enhanced_df)} rows for location enhancement...")

        for idx, row in enhanced_df.iterrows():
            if pd.notna(row.get('latitude')) and pd.notna(row.get('longitude')):
                context = self._get_location_context(row['latitude'], row['longitude'])
                location_contexts.append(context)
            else:
                location_contexts.append(LocationContext((np.nan, np.nan)))

        # Add new columns with location intelligence
        enhanced_df['ocean_basin'] = [ctx.ocean_basin if ctx.ocean_basin else "Unknown" for ctx in location_contexts]
        enhanced_df['marine_region'] = [ctx.marine_region if ctx.marine_region else "Unknown" for ctx in location_contexts]
        enhanced_df['distance_to_coast'] = [ctx.distance_to_coast for ctx in location_contexts]
        enhanced_df['oceanographic_region'] = [ctx.oceanographic_region if ctx.oceanographic_region else "Unknown" for ctx in location_contexts]
        enhanced_df['country_eez'] = [ctx.country for ctx in location_contexts]
        enhanced_df['circulation_feature'] = [ctx.circulation_feature if ctx.circulation_feature else "General" for ctx in location_contexts]

        print(f"Enhanced dataframe columns: {list(enhanced_df.columns)}")
        print(f"Ocean basins found: {enhanced_df['ocean_basin'].value_counts().to_dict()}")

        return enhanced_df

    def _get_location_context(self, lat: float, lon: float) -> LocationContext:
        """Get comprehensive location context for coordinates"""
        context = LocationContext(coordinates=(lat, lon))

        try:
            # Reverse geocoding for political boundaries
            if GEOSPATIAL_AVAILABLE:
                results = rg.search((lat, lon))
                if results:
                    result = results[0]
                    context.country_code = result.get('cc')
                    context.admin1 = result.get('admin1')
                    context.admin2 = result.get('admin2')

                    # Get country name
                    if context.country_code:
                        try:
                            country = pycountry.countries.get(alpha_2=context.country_code)
                            context.country = country.name if country else None
                        except:
                            pass

            # Ocean basin identification
            context.ocean_basin = self._identify_ocean_basin(lat, lon)
            context.marine_region = self._identify_marine_region(lat, lon)

            # Oceanographic region classification
            context.oceanographic_region = self._classify_oceanographic_region(lat, lon)

            # Circulation features
            context.circulation_feature = self._identify_circulation_features(lat, lon)

            # Distance to coast (simplified calculation)
            context.distance_to_coast = self._estimate_distance_to_coast(lat, lon)

            # Depth zone classification
            context.depth_zone = self._classify_depth_zone(lat, lon)

        except Exception as e:
            # Fallback to basic classification if detailed analysis fails
            context.ocean_basin = self._identify_ocean_basin(lat, lon)
            context.marine_region = "Unknown"

        return context

    def _identify_ocean_basin(self, lat: float, lon: float) -> str:
        """Identify ocean basin based on coordinates"""
        for basin_name, basin_info in self.ocean_basins.items():
            bounds = basin_info['bounds']
            if (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                bounds['lon_min'] <= lon <= bounds['lon_max']):
                return basin_name

        # General Indian Ocean classification
        if -60 <= lat <= 30 and 20 <= lon <= 140:
            if lat > 0:
                return "Northern Indian Ocean"
            else:
                return "Southern Indian Ocean"

        return "Other Indian Ocean"

    def _identify_marine_region(self, lat: float, lon: float) -> str:
        """Identify specific marine region"""
        # Check special regions first
        for region_name, region_info in self.special_regions.items():
            bounds = region_info['bounds']
            if (bounds['lat_min'] <= lat <= bounds['lat_max'] and
                bounds['lon_min'] <= lon <= bounds['lon_max']):
                return region_name

        # Regional classifications based on oceanographic knowledge
        if 0 <= lat <= 30 and 50 <= lon <= 80:
            if 15 <= lat <= 25:
                return "Arabian Sea Central"
            elif lat < 15:
                return "Arabian Sea Equatorial"
            else:
                return "Arabian Sea Northern"

        elif 5 <= lat <= 25 and 80 <= lon <= 100:
            if lon > 90:
                return "Bay of Bengal Eastern"
            else:
                return "Bay of Bengal Western"

        elif -60 <= lat <= -30:
            if lon < 70:
                return "Southern Ocean Atlantic Sector"
            elif lon < 110:
                return "Southern Ocean Indian Sector"
            else:
                return "Southern Ocean Pacific Sector"

        return "Open Ocean"

    def _classify_oceanographic_region(self, lat: float, lon: float) -> str:
        """Classify based on oceanographic characteristics"""
        # Equatorial region
        if -5 <= lat <= 5:
            return "Equatorial"

        # Tropical regions
        elif 5 < lat <= 23.5 or -23.5 <= lat < -5:
            return "Tropical"

        # Subtropical regions
        elif 23.5 < lat <= 35 or -35 <= lat < -23.5:
            return "Subtropical"

        # Temperate regions
        elif 35 < lat <= 50 or -50 <= lat < -35:
            return "Temperate"

        # Polar regions
        elif lat > 50 or lat < -50:
            return "Polar/Subpolar"

        return "Transitional"

    def _identify_circulation_features(self, lat: float, lon: float) -> str:
        """Identify major circulation features"""
        # Arabian Sea features
        if 10 <= lat <= 25 and 55 <= lon <= 75:
            return "Somali Current System"

        # Bay of Bengal features
        elif 8 <= lat <= 20 and 85 <= lon <= 95:
            return "East India Coastal Current"

        # Equatorial features
        elif -5 <= lat <= 5 and 50 <= lon <= 100:
            return "Equatorial Current System"

        # Southern Ocean features
        elif -60 <= lat <= -40:
            return "Antarctic Circumpolar Current"

        # Agulhas system
        elif -40 <= lat <= -25 and 25 <= lon <= 45:
            return "Agulhas Current System"

        return "General Circulation"

    def _estimate_distance_to_coast(self, lat: float, lon: float) -> float:
        """Estimate distance to nearest coast (simplified)"""
        # This is a simplified estimation - in production, use detailed coastline data

        # Major land masses in Indian Ocean region
        coast_points = [
            # India
            (20.0, 77.0), (15.0, 74.0), (10.0, 76.0), (8.0, 78.0),
            # Arabian Peninsula
            (25.0, 55.0), (20.0, 58.0), (15.0, 52.0),
            # Africa
            (-10.0, 40.0), (-20.0, 35.0), (-30.0, 30.0),
            # Australia
            (-35.0, 135.0), (-25.0, 115.0), (-12.0, 130.0),
            # Madagascar
            (-20.0, 47.0), (-15.0, 50.0),
            # Sri Lanka
            (7.0, 81.0)
        ]

        min_distance = float('inf')

        if GEOSPATIAL_AVAILABLE:
            for coast_lat, coast_lon in coast_points:
                try:
                    distance = great_circle((lat, lon), (coast_lat, coast_lon)).kilometers
                    min_distance = min(min_distance, distance)
                except:
                    continue

        return min_distance if min_distance != float('inf') else None

    def _classify_depth_zone(self, lat: float, lon: float) -> str:
        """Classify expected depth zone based on location"""
        # Simplified bathymetry classification

        # Continental shelf regions (shallow)
        if ((0 <= lat <= 30 and 65 <= lon <= 85) or  # Indian continental shelf
            (5 <= lat <= 25 and 80 <= lon <= 95) or  # Bay of Bengal shelf
            (-35 <= lat <= -10 and 25 <= lon <= 45)):  # African shelf
            return "Continental Shelf"

        # Deep ocean basins
        elif (-60 <= lat <= -30) or (lat < -30 and 60 <= lon <= 120):
            return "Abyssal Plain"

        # Mid-ocean ridge regions
        elif (-30 <= lat <= 0 and 60 <= lon <= 80):
            return "Mid-Ocean Ridge"

        return "Deep Ocean"

    def generate_regional_analytics(self, df: pd.DataFrame) -> List[RegionalAnalysis]:
        """Generate comprehensive regional analytics"""
        if df.empty or 'latitude' not in df.columns or 'longitude' not in df.columns:
            return []

        # Enhance data with location intelligence
        enhanced_df = self.enhance_location_data(df)

        regional_analyses = []

        # Group by ocean basin for analysis
        if 'ocean_basin' not in enhanced_df.columns:
            print("Warning: ocean_basin column not found in enhanced dataframe")
            return []

        # Filter out Unknown basins and group
        valid_basins = enhanced_df[enhanced_df['ocean_basin'] != "Unknown"]
        if valid_basins.empty:
            print("Warning: No valid ocean basins found")
            return []

        for basin_name, basin_data in valid_basins.groupby('ocean_basin'):
            if len(basin_data) < 2:  # Skip regions with too little data (reduced threshold)
                continue

            analysis = self._analyze_region(basin_name, basin_data)
            regional_analyses.append(analysis)

        return regional_analyses

    def _analyze_region(self, region_name: str, data: pd.DataFrame) -> RegionalAnalysis:
        """Perform detailed analysis of a specific region"""

        # Spatial bounds
        spatial_bounds = {
            'lat_min': float(data['latitude'].min()),
            'lat_max': float(data['latitude'].max()),
            'lon_min': float(data['longitude'].min()),
            'lon_max': float(data['longitude'].max()),
            'center_lat': float(data['latitude'].mean()),
            'center_lon': float(data['longitude'].mean())
        }

        # Oceanographic features from basin definition
        features = []
        if region_name in self.ocean_basins:
            features = self.ocean_basins[region_name]['features']

        # Environmental context
        environmental_context = {}

        # Temperature analysis
        if 'temperature' in data.columns and data['temperature'].notna().sum() > 0:
            temp_data = data['temperature'].dropna()
            environmental_context['temperature'] = {
                'mean': float(temp_data.mean()),
                'std': float(temp_data.std()),
                'min': float(temp_data.min()),
                'max': float(temp_data.max()),
                'range': float(temp_data.max() - temp_data.min())
            }

        # Salinity analysis
        if 'salinity' in data.columns and data['salinity'].notna().sum() > 0:
            sal_data = data['salinity'].dropna()
            environmental_context['salinity'] = {
                'mean': float(sal_data.mean()),
                'std': float(sal_data.std()),
                'min': float(sal_data.min()),
                'max': float(sal_data.max()),
                'range': float(sal_data.max() - sal_data.min())
            }

        # Depth analysis
        if 'depth' in data.columns and data['depth'].notna().sum() > 0:
            depth_data = data['depth'].dropna()
            environmental_context['depth'] = {
                'mean': float(depth_data.mean()),
                'std': float(depth_data.std()),
                'min': float(depth_data.min()),
                'max': float(depth_data.max()),
                'surface_measurements': int(len(depth_data[depth_data < 100])),
                'deep_measurements': int(len(depth_data[depth_data > 1000]))
            }

        # Circulation features
        if 'circulation_feature' in data.columns:
            circulation_counts = data['circulation_feature'].value_counts().to_dict()
            environmental_context['circulation_features'] = circulation_counts

        # Distance to coast analysis
        if 'distance_to_coast' in data.columns and data['distance_to_coast'].notna().sum() > 0:
            coast_dist = data['distance_to_coast'].dropna()
            environmental_context['coastal_proximity'] = {
                'mean_distance_km': float(coast_dist.mean()),
                'min_distance_km': float(coast_dist.min()),
                'coastal_measurements': int(len(coast_dist[coast_dist < 200])),  # Within 200km
                'open_ocean_measurements': int(len(coast_dist[coast_dist > 500]))  # Beyond 500km
            }

        # Statistical summary
        statistical_summary = {
            'measurement_density': len(data) / max(1, (spatial_bounds['lat_max'] - spatial_bounds['lat_min']) *
                                                  (spatial_bounds['lon_max'] - spatial_bounds['lon_min'])),
            'spatial_coverage_lat': spatial_bounds['lat_max'] - spatial_bounds['lat_min'],
            'spatial_coverage_lon': spatial_bounds['lon_max'] - spatial_bounds['lon_min'],
            'data_completeness': data.notna().mean().mean()
        }

        # Data quality metrics
        data_quality_metrics = {
            'coordinate_completeness': data[['latitude', 'longitude']].notna().all(axis=1).mean(),
            'parameter_completeness': data[['temperature', 'salinity']].notna().mean().mean() if 'temperature' in data.columns else 0,
            'temporal_consistency': 1.0,  # Placeholder - would analyze temporal gaps
            'spatial_clustering': self._calculate_spatial_clustering(data)
        }

        return RegionalAnalysis(
            region_name=region_name,
            measurement_count=len(data),
            float_count=data['float_id'].nunique() if 'float_id' in data.columns else 0,
            spatial_bounds=spatial_bounds,
            oceanographic_features=features,
            environmental_context=environmental_context,
            statistical_summary=statistical_summary,
            data_quality_metrics=data_quality_metrics
        )

    def _calculate_spatial_clustering(self, data: pd.DataFrame) -> float:
        """Calculate spatial clustering coefficient"""
        if len(data) < 3:
            return 0.0

        # Simple clustering metric based on standard deviation
        lat_std = data['latitude'].std()
        lon_std = data['longitude'].std()

        # Normalize based on typical ocean basin sizes
        clustering_score = 1.0 / (1.0 + (lat_std + lon_std) / 10.0)
        return float(clustering_score)

    def get_location_based_context(self, lat: float, lon: float, depth: Optional[float] = None) -> Dict[str, Any]:
        """Get rich location context for RAG enhancement"""
        context = self._get_location_context(lat, lon)

        # Build comprehensive context for AI
        location_context = {
            'coordinates': f"{lat:.2f}°, {lon:.2f}°",
            'ocean_basin': context.ocean_basin,
            'marine_region': context.marine_region,
            'oceanographic_region': context.oceanographic_region,
            'circulation_feature': context.circulation_feature,
            'country_context': context.country,
            'administrative_region': context.admin1
        }

        # Add depth-specific context
        if depth is not None:
            if depth < 100:
                location_context['depth_context'] = "surface mixed layer"
            elif depth < 500:
                location_context['depth_context'] = "intermediate waters"
            elif depth < 1000:
                location_context['depth_context'] = "deep waters"
            else:
                location_context['depth_context'] = "abyssal depths"

        # Add oceanographic insights
        basin_info = self.ocean_basins.get(context.ocean_basin, {})
        if basin_info:
            location_context['oceanographic_features'] = basin_info.get('features', [])

        # Add seasonal context (simplified)
        location_context['seasonal_notes'] = self._get_seasonal_context(lat, context.ocean_basin)

        return location_context

    def _get_seasonal_context(self, lat: float, ocean_basin: str) -> List[str]:
        """Get seasonal oceanographic context"""
        seasonal_notes = []

        if ocean_basin == "Arabian Sea":
            seasonal_notes.extend([
                "Southwest monsoon (June-September) drives strong upwelling",
                "Northeast monsoon (December-March) brings cooler, drier conditions",
                "Intermonsoon periods show transitional characteristics"
            ])
        elif ocean_basin == "Bay of Bengal":
            seasonal_notes.extend([
                "Strong seasonal stratification due to river discharge",
                "Cyclone season (April-December) affects upper ocean structure",
                "Winter cooling creates stronger mixing"
            ])
        elif "Southern" in ocean_basin:
            seasonal_notes.extend([
                "Austral summer (Dec-Feb) shows maximum warming",
                "Austral winter (Jun-Aug) deepens mixed layer",
                "Strong westerly winds drive surface currents"
            ])

        # Latitudinal seasonal effects
        if lat > 0:
            seasonal_notes.append("Northern hemisphere seasonal cycle")
        else:
            seasonal_notes.append("Southern hemisphere seasonal cycle")

        return seasonal_notes
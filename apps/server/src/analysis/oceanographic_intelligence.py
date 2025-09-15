"""
Advanced Oceanographic Intelligence Engine
Leverages powerful scientific libraries for sophisticated marine data analysis
"""

import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import warnings
warnings.filterwarnings('ignore')
# Core scientific libraries
from scipy import stats
from sklearn.ensemble import IsolationForest
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler

# Statistical analysis
import statsmodels.api as sm

# Anomaly detection
try:
    from pyod.models.isolation import IForest
    from pyod.models.lof import LOF
    PYOD_AVAILABLE = True
except ImportError:
    PYOD_AVAILABLE = False

# Oceanographic calculations
try:
    import gsw  # Gibbs SeaWater toolbox for oceanographic calculations
    GSW_AVAILABLE = True
except ImportError:
    GSW_AVAILABLE = False


@dataclass
class AnalysisResult:
    """Container for analysis results"""
    analysis_type: str
    primary_findings: List[str]
    statistical_summary: Dict[str, float]
    anomalies: List[Dict] = None
    comparative_data: Dict[str, Any] = None
    quality_metrics: Dict[str, float] = None
    recommendations: List[str] = None


class OceanographicIntelligence:
    """Advanced oceanographic data analysis with scientific rigor"""

    def __init__(self):
        self.scaler = StandardScaler()
        self.anomaly_detectors = {}
        if PYOD_AVAILABLE:
            self.anomaly_detectors['isolation'] = IForest(contamination=0.1)
            self.anomaly_detectors['lof'] = LOF(contamination=0.1)

    def analyze_query_intent(self, query: str, data: List[Dict]) -> str:
        """Intelligently determine what type of analysis the user wants"""
        query_lower = query.lower()

        # Complex analysis patterns
        if any(word in query_lower for word in ['anomaly', 'anomalies', 'unusual', 'outlier', 'strange']):
            return 'anomaly_detection'
        elif any(word in query_lower for word in ['compare', 'comparison', 'difference', 'vs', 'versus', 'between']):
            return 'comparative_analysis'
        elif any(word in query_lower for word in ['trend', 'time series', 'temporal', 'over time', 'seasonal']):
            return 'temporal_analysis'
        elif any(word in query_lower for word in ['deep', 'depth', 'vertical', 'profile', 'stratification']):
            return 'depth_profile_analysis'
        elif any(word in query_lower for word in ['pattern', 'cluster', 'group', 'similar', 'classification']):
            return 'pattern_analysis'
        elif any(word in query_lower for word in ['correlation', 'relationship', 'association']):
            return 'correlation_analysis'
        elif any(word in query_lower for word in ['distribution', 'statistical', 'stats', 'summary']):
            return 'statistical_analysis'
        elif any(word in query_lower for word in ['quality', 'validate', 'check', 'assessment']):
            return 'quality_assessment'
        else:
            return 'exploratory_analysis'

    def perform_intelligent_analysis(self, query: str, data: List[Dict]) -> AnalysisResult:
        """Main analysis engine that adapts to query complexity"""
        if not data:
            return AnalysisResult("empty", ["No data available for analysis"], {})

        # Convert to DataFrame for analysis
        df = pd.DataFrame(data)

        # Determine analysis type
        analysis_type = self.analyze_query_intent(query, data)

        # Route to appropriate analysis method
        if analysis_type == 'anomaly_detection':
            return self._detect_anomalies(df, query)
        elif analysis_type == 'comparative_analysis':
            return self._perform_comparative_analysis(df, query)
        elif analysis_type == 'temporal_analysis':
            return self._analyze_temporal_patterns(df, query)
        elif analysis_type == 'depth_profile_analysis':
            return self._analyze_depth_profiles(df, query)
        elif analysis_type == 'pattern_analysis':
            return self._discover_patterns(df, query)
        elif analysis_type == 'correlation_analysis':
            return self._analyze_correlations(df, query)
        elif analysis_type == 'statistical_analysis':
            return self._comprehensive_statistics(df, query)
        elif analysis_type == 'quality_assessment':
            return self._assess_data_quality(df, query)
        else:
            return self._exploratory_analysis(df, query)

    def _detect_anomalies(self, df: pd.DataFrame, query: str) -> AnalysisResult:
        """Advanced anomaly detection using multiple algorithms"""
        findings = []
        anomalies = []

        # Prepare numerical features
        numeric_cols = ['temperature', 'salinity', 'depth', 'pressure', 'latitude', 'longitude']
        available_cols = [col for col in numeric_cols if col in df.columns and df[col].notna().sum() > 10]

        if len(available_cols) < 2:
            return AnalysisResult("anomaly_detection",
                                ["Insufficient numerical data for anomaly detection"], {})

        # Create feature matrix
        feature_data = df[available_cols].dropna()
        if len(feature_data) < 20:
            return AnalysisResult("anomaly_detection",
                                ["Insufficient data points for reliable anomaly detection"], {})

        # Multiple anomaly detection approaches
        anomaly_methods = {}

        # 1. Statistical outliers (Z-score)
        z_scores = np.abs(stats.zscore(feature_data))
        statistical_outliers = (z_scores > 3).any(axis=1)
        anomaly_methods['statistical'] = statistical_outliers

        # 2. Isolation Forest
        iso_forest = IsolationForest(contamination=0.1, random_state=42)
        iso_outliers = iso_forest.fit_predict(feature_data) == -1
        anomaly_methods['isolation_forest'] = iso_outliers

        # 3. DBSCAN clustering for spatial anomalies
        if 'latitude' in available_cols and 'longitude' in available_cols:
            geo_data = feature_data[['latitude', 'longitude']].values
            dbscan = DBSCAN(eps=2, min_samples=3)  # 2-degree tolerance
            clusters = dbscan.fit_predict(geo_data)
            spatial_outliers = clusters == -1
            anomaly_methods['spatial'] = spatial_outliers

        # Combine results using consensus
        anomaly_consensus = pd.DataFrame(anomaly_methods)
        consensus_anomalies = (anomaly_consensus.sum(axis=1) >= 2)  # At least 2 methods agree

        n_anomalies = consensus_anomalies.sum()
        findings.append(f"Detected {n_anomalies} significant anomalies using multiple detection methods")

        if n_anomalies > 0:
            anomaly_indices = feature_data.index[consensus_anomalies]
            for idx in anomaly_indices[:5]:  # Show top 5 anomalies
                row = df.loc[idx]
                anomaly_detail = {
                    'index': int(idx),
                    'location': f"({row.get('latitude', 'N/A'):.2f}, {row.get('longitude', 'N/A'):.2f})",
                    'depth': row.get('depth', 'N/A'),
                    'temperature': row.get('temperature', 'N/A'),
                    'salinity': row.get('salinity', 'N/A'),
                    'detection_methods': [method for method, detected in anomaly_consensus.loc[idx].items() if detected]
                }
                anomalies.append(anomaly_detail)

            findings.append(f"Anomalies concentrated in: {self._describe_anomaly_patterns(df, anomaly_indices)}")

        # Statistical summary
        stats_summary = {
            'total_points': len(df),
            'anomaly_rate': float(n_anomalies / len(feature_data) * 100),
            'detection_confidence': float(anomaly_consensus.sum(axis=1).mean())
        }

        return AnalysisResult(
            analysis_type="anomaly_detection",
            primary_findings=findings,
            statistical_summary=stats_summary,
            anomalies=anomalies,
            recommendations=self._generate_anomaly_recommendations(df, consensus_anomalies)
        )

    def _perform_comparative_analysis(self, df: pd.DataFrame, query: str) -> AnalysisResult:
        """Intelligent comparative analysis between regions/conditions"""
        findings = []
        comparative_data = {}

        # Extract comparison subjects from query
        regions = self._extract_regions_from_query(query)
        parameters = self._extract_parameters_from_query(query)
        depth_criteria = self._extract_depth_criteria_from_query(query)

        if len(regions) < 2:
            # Auto-detect comparison groups if not explicit
            regions = self._auto_detect_comparison_groups(df)

        if not parameters:
            parameters = ['temperature', 'salinity']  # Default comparison parameters

        findings.append(f"Comparing {len(regions)} regions/conditions across {len(parameters)} parameters")

        # Perform statistical comparisons
        for param in parameters:
            if param in df.columns and df[param].notna().sum() > 10:
                param_comparison = {}

                for region in regions:
                    region_data = self._filter_data_by_region(df, region, depth_criteria)
                    if len(region_data) > 0:
                        param_comparison[region] = {
                            'mean': float(region_data[param].mean()),
                            'std': float(region_data[param].std()),
                            'count': int(len(region_data)),
                            'range': [float(region_data[param].min()), float(region_data[param].max())]
                        }

                # Statistical significance testing
                if len(param_comparison) >= 2:
                    groups = list(param_comparison.keys())
                    group1_data = self._filter_data_by_region(df, groups[0], depth_criteria)[param].dropna()
                    group2_data = self._filter_data_by_region(df, groups[1], depth_criteria)[param].dropna()

                    if len(group1_data) > 5 and len(group2_data) > 5:
                        t_stat, p_value = stats.ttest_ind(group1_data, group2_data)

                        param_comparison['statistical_test'] = {
                            'test': 't-test',
                            'p_value': float(p_value),
                            'significant': p_value < 0.05,
                            'effect_size': float(abs(group1_data.mean() - group2_data.mean()) /
                                               np.sqrt((group1_data.var() + group2_data.var()) / 2))
                        }

                comparative_data[param] = param_comparison

        # Generate findings
        for param, comparison in comparative_data.items():
            if 'statistical_test' in comparison:
                test_result = comparison['statistical_test']
                if test_result['significant']:
                    findings.append(f"Significant difference in {param} between regions (p={test_result['p_value']:.4f})")
                else:
                    findings.append(f"No significant difference in {param} between regions (p={test_result['p_value']:.4f})")

        return AnalysisResult(
            analysis_type="comparative_analysis",
            primary_findings=findings,
            statistical_summary={'regions_compared': len(regions), 'parameters_analyzed': len(parameters)},
            comparative_data=comparative_data,
            recommendations=self._generate_comparative_recommendations(comparative_data)
        )

    def _analyze_depth_profiles(self, df: pd.DataFrame, query: str) -> AnalysisResult:
        """Advanced depth profile analysis with oceanographic calculations"""
        findings = []

        if 'depth' not in df.columns or 'temperature' not in df.columns:
            return AnalysisResult("depth_profile",
                                ["Insufficient depth and temperature data for profile analysis"], {})

        # Clean and prepare depth data
        profile_data = df[['depth', 'temperature', 'salinity']].dropna()
        if len(profile_data) < 20:
            return AnalysisResult("depth_profile",
                                ["Insufficient data points for depth profile analysis"], {})

        # Sort by depth for profile analysis
        profile_data = profile_data.sort_values('depth')

        # Detect thermocline
        thermocline_info = self._detect_thermocline(profile_data)
        if thermocline_info:
            findings.extend(thermocline_info)

        # Analyze temperature gradient
        temp_gradient = np.gradient(profile_data['temperature'], profile_data['depth'])
        max_gradient_idx = np.argmax(np.abs(temp_gradient))
        max_gradient_depth = profile_data.iloc[max_gradient_idx]['depth']

        findings.append(f"Maximum temperature gradient at {max_gradient_depth:.1f}m depth")

        # Water mass identification using T-S analysis
        if 'salinity' in df.columns and df['salinity'].notna().sum() > 10:
            water_masses = self._identify_water_masses(profile_data)
            if water_masses:
                findings.extend(water_masses)

        # Oceanographic calculations using GSW if available
        if GSW_AVAILABLE and 'salinity' in profile_data.columns:
            findings.extend(self._calculate_oceanographic_properties(profile_data))

        # Statistical summary
        depth_stats = {
            'depth_range': [float(profile_data['depth'].min()), float(profile_data['depth'].max())],
            'temperature_range': [float(profile_data['temperature'].min()), float(profile_data['temperature'].max())],
            'avg_temperature_gradient': float(np.mean(temp_gradient)),
            'profile_points': int(len(profile_data))
        }

        return AnalysisResult(
            analysis_type="depth_profile_analysis",
            primary_findings=findings,
            statistical_summary=depth_stats,
            recommendations=self._generate_depth_profile_recommendations(profile_data, temp_gradient)
        )

    def _comprehensive_statistics(self, df: pd.DataFrame, query: str) -> AnalysisResult:
        """Comprehensive statistical analysis with oceanographic insights"""
        findings = []
        stats_summary = {}

        # Core oceanographic parameters
        params = ['temperature', 'salinity', 'depth', 'pressure']
        available_params = [p for p in params if p in df.columns and df[p].notna().sum() > 0]

        for param in available_params:
            data = df[param].dropna()

            # Basic statistics
            param_stats = {
                'mean': float(data.mean()),
                'median': float(data.median()),
                'std': float(data.std()),
                'min': float(data.min()),
                'max': float(data.max()),
                'count': int(len(data)),
                'skewness': float(stats.skew(data)),
                'kurtosis': float(stats.kurtosis(data))
            }

            # Distribution analysis
            normality_stat, normality_p = stats.normaltest(data)
            param_stats['is_normal'] = normality_p > 0.05

            # Percentiles
            param_stats['percentiles'] = {
                '25th': float(np.percentile(data, 25)),
                '75th': float(np.percentile(data, 75)),
                '90th': float(np.percentile(data, 90)),
                '95th': float(np.percentile(data, 95))
            }

            stats_summary[param] = param_stats

            # Generate findings
            if param == 'temperature':
                temp_insights = self._analyze_temperature_distribution(data)
                findings.extend(temp_insights)
            elif param == 'salinity':
                salinity_insights = self._analyze_salinity_distribution(data)
                findings.extend(salinity_insights)

        # Cross-parameter analysis
        if len(available_params) >= 2:
            correlation_matrix = df[available_params].corr()
            stats_summary['correlations'] = correlation_matrix.to_dict()

            # Find strongest correlations
            strong_corrs = self._find_strong_correlations(correlation_matrix)
            findings.extend(strong_corrs)

        # Spatial distribution analysis
        if 'latitude' in df.columns and 'longitude' in df.columns:
            spatial_stats = self._analyze_spatial_distribution(df)
            stats_summary['spatial'] = spatial_stats
            findings.extend([f"Data spans {spatial_stats['lat_range']:.1f}° latitude and {spatial_stats['lon_range']:.1f}° longitude"])

        return AnalysisResult(
            analysis_type="statistical_analysis",
            primary_findings=findings,
            statistical_summary=stats_summary,
            recommendations=self._generate_statistical_recommendations(stats_summary)
        )

    # Helper methods for analysis
    def _extract_regions_from_query(self, query: str) -> List[str]:
        """Extract region names from query text"""
        regions = []
        region_keywords = ['arabian sea', 'bay of bengal', 'indian ocean', 'southern indian', 'northern indian']

        query_lower = query.lower()
        for region in region_keywords:
            if region in query_lower:
                regions.append(region)

        return regions or ['region_1', 'region_2']  # Default regions if none found

    def _extract_parameters_from_query(self, query: str) -> List[str]:
        """Extract parameter names from query text"""
        parameters = []
        param_keywords = ['temperature', 'salinity', 'pressure', 'depth']

        query_lower = query.lower()
        for param in param_keywords:
            if param in query_lower:
                parameters.append(param)

        return parameters

    def _extract_depth_criteria_from_query(self, query: str) -> Optional[Dict]:
        """Extract depth criteria from query"""
        import re

        query_lower = query.lower()

        # Look for depth specifications
        depth_patterns = [
            r'below (\d+)m?',
            r'above (\d+)m?',
            r'depth.*?(\d+).*?(\d+)',
            r'(\d+).*?meters?'
        ]

        for pattern in depth_patterns:
            match = re.search(pattern, query_lower)
            if match:
                if 'below' in pattern:
                    return {'operator': '>=', 'value': float(match.group(1))}
                elif 'above' in pattern:
                    return {'operator': '<=', 'value': float(match.group(1))}

        return None

    def _filter_data_by_region(self, df: pd.DataFrame, region: str, depth_criteria: Optional[Dict] = None) -> pd.DataFrame:
        """Filter data by region and depth criteria"""
        # This is a simplified version - would integrate with enhanced region resolver
        filtered_df = df.copy()

        if depth_criteria:
            op = depth_criteria['operator']
            value = depth_criteria['value']
            if op == '>=':
                filtered_df = filtered_df[filtered_df['depth'] >= value]
            elif op == '<=':
                filtered_df = filtered_df[filtered_df['depth'] <= value]

        return filtered_df

    def _detect_thermocline(self, profile_data: pd.DataFrame) -> List[str]:
        """Detect thermocline in temperature profile"""
        findings = []

        if len(profile_data) < 10:
            return findings

        # Calculate temperature gradient
        temp_gradient = np.gradient(profile_data['temperature'], profile_data['depth'])

        # Find depth of maximum temperature gradient (thermocline center)
        max_gradient_idx = np.argmax(np.abs(temp_gradient))
        thermocline_depth = profile_data.iloc[max_gradient_idx]['depth']
        max_gradient = temp_gradient[max_gradient_idx]

        if abs(max_gradient) > 0.1:  # Significant gradient threshold
            findings.append(f"Thermocline detected at {thermocline_depth:.1f}m with gradient {max_gradient:.3f}°C/m")

            # Classify thermocline strength
            if abs(max_gradient) > 0.5:
                strength = "strong"
            elif abs(max_gradient) > 0.2:
                strength = "moderate"
            else:
                strength = "weak"

            findings.append(f"Thermocline strength: {strength}")

        return findings

    def _generate_anomaly_recommendations(self, df: pd.DataFrame, anomalies: pd.Series) -> List[str]:
        """Generate recommendations based on anomaly analysis"""
        recommendations = []

        if anomalies.sum() > len(df) * 0.1:
            recommendations.append("High anomaly rate detected - consider data quality assessment")

        recommendations.append("Investigate anomalous measurements for potential sensor errors or interesting phenomena")
        recommendations.append("Consider temporal analysis to identify if anomalies cluster in time")

        return recommendations

    def _describe_anomaly_patterns(self, df: pd.DataFrame, anomaly_indices: pd.Index) -> str:
        """Describe patterns in detected anomalies"""
        anomaly_data = df.loc[anomaly_indices]

        if 'depth' in anomaly_data.columns:
            depth_pattern = anomaly_data['depth'].describe()
            if depth_pattern['75%'] > 1000:
                return "deep water regions"
            elif depth_pattern['25%'] < 100:
                return "surface waters"
            else:
                return "mid-depth waters"

        return "various depths"

    # Additional helper methods would continue here...
    def _auto_detect_comparison_groups(self, df: pd.DataFrame) -> List[str]:
        """Auto-detect natural comparison groups in data"""
        # Simple implementation - could be enhanced with clustering
        return ['group_1', 'group_2']

    def _identify_water_masses(self, profile_data: pd.DataFrame) -> List[str]:
        """Identify water masses using T-S characteristics"""
        findings = []
        # Placeholder for water mass identification logic
        return findings

    def _calculate_oceanographic_properties(self, profile_data: pd.DataFrame) -> List[str]:
        """Calculate advanced oceanographic properties using GSW"""
        findings = []
        # Placeholder for GSW calculations
        return findings

    def _analyze_temperature_distribution(self, temp_data: pd.Series) -> List[str]:
        """Analyze temperature distribution characteristics"""
        findings = []
        mean_temp = temp_data.mean()

        if mean_temp > 25:
            findings.append("Tropical water masses detected")
        elif mean_temp < 5:
            findings.append("Cold/deep water masses detected")
        else:
            findings.append("Temperate water conditions observed")

        return findings

    def _analyze_salinity_distribution(self, salinity_data: pd.Series) -> List[str]:
        """Analyze salinity distribution characteristics"""
        findings = []
        mean_salinity = salinity_data.mean()

        if mean_salinity > 36:
            findings.append("High salinity waters - possible evaporation or deep water influence")
        elif mean_salinity < 34:
            findings.append("Low salinity waters - possible freshwater input or precipitation")

        return findings

    def _find_strong_correlations(self, correlation_matrix: pd.DataFrame) -> List[str]:
        """Find and describe strong correlations"""
        findings = []

        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr = correlation_matrix.iloc[i, j]
                if abs(corr) > 0.7:
                    param1 = correlation_matrix.columns[i]
                    param2 = correlation_matrix.columns[j]
                    strength = "strong positive" if corr > 0 else "strong negative"
                    findings.append(f"{strength.title()} correlation between {param1} and {param2} (r={corr:.3f})")

        return findings

    def _analyze_spatial_distribution(self, df: pd.DataFrame) -> Dict:
        """Analyze spatial distribution of data"""
        lat_range = df['latitude'].max() - df['latitude'].min()
        lon_range = df['longitude'].max() - df['longitude'].min()

        return {
            'lat_range': float(lat_range),
            'lon_range': float(lon_range),
            'center_lat': float(df['latitude'].mean()),
            'center_lon': float(df['longitude'].mean())
        }

    def _generate_comparative_recommendations(self, comparative_data: Dict) -> List[str]:
        """Generate recommendations for comparative analysis"""
        recommendations = []
        recommendations.append("Consider temporal analysis to understand if differences are consistent over time")
        recommendations.append("Investigate environmental factors that might explain regional differences")
        return recommendations

    def _generate_depth_profile_recommendations(self, profile_data: pd.DataFrame, temp_gradient: np.ndarray) -> List[str]:
        """Generate recommendations for depth profile analysis"""
        recommendations = []
        recommendations.append("Consider T-S analysis for water mass identification")
        recommendations.append("Analyze seasonal variations in thermocline depth and strength")
        return recommendations

    def _generate_statistical_recommendations(self, stats_summary: Dict) -> List[str]:
        """Generate recommendations for statistical analysis"""
        recommendations = []
        recommendations.append("Consider quality control procedures for outlying values")
        recommendations.append("Investigate correlations with environmental drivers")
        return recommendations
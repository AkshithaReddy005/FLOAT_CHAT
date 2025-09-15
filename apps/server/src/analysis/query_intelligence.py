"""
Intelligent Query Understanding and Enhancement System
Leverages NLP and domain knowledge to understand complex oceanographic queries
"""

import re
import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from sklearn.feature_extraction.text import TfidfVectorizer
import pandas as pd

@dataclass
class QueryEnhancement:
    """Enhanced query understanding"""
    original_query: str
    intent: str
    complexity_level: str
    required_analysis: List[str]
    data_requirements: Dict[str, any]
    suggested_parameters: List[str]
    confidence_score: float
    enhanced_filters: Dict[str, any]


class QueryIntelligence:
    """Advanced query understanding for oceanographic research"""

    def __init__(self):
        # Oceanographic domain vocabulary
        self.domain_vocabulary = {
            'parameters': {
                'temperature': ['temp', 'temperature', 'thermal', 'heat', 'warming', 'cooling'],
                'salinity': ['salinity', 'salt', 'saline', 'conductivity', 'psu', 'pss'],
                'density': ['density', 'sigma', 'potential density', 'rho'],
                'pressure': ['pressure', 'depth pressure', 'hydrostatic'],
                'oxygen': ['oxygen', 'o2', 'dissolved oxygen', 'do'],
                'chlorophyll': ['chlorophyll', 'chl', 'phytoplankton', 'productivity']
            },
            'regions': {
                'arabian_sea': ['arabian sea', 'arabian', 'west indian ocean', 'oman sea'],
                'bay_of_bengal': ['bay of bengal', 'bengal bay', 'east indian ocean', 'bengal'],
                'indian_ocean': ['indian ocean', 'indian', 'indo-pacific'],
                'southern_ocean': ['southern ocean', 'antarctic ocean', 'circumpolar'],
                'equatorial': ['equatorial', 'tropical', 'itra', 'equator']
            },
            'analysis_types': {
                'anomaly': ['anomaly', 'anomalies', 'unusual', 'outlier', 'strange', 'abnormal'],
                'trend': ['trend', 'time series', 'temporal', 'seasonal', 'annual', 'monthly'],
                'comparison': ['compare', 'comparison', 'versus', 'vs', 'difference', 'between'],
                'profile': ['profile', 'vertical', 'depth', 'stratification', 'layers'],
                'correlation': ['correlation', 'relationship', 'association', 'connected'],
                'distribution': ['distribution', 'spread', 'histogram', 'statistical']
            },
            'depth_terms': {
                'surface': ['surface', 'top', 'mixed layer', 'sst', 'sea surface'],
                'shallow': ['shallow', 'upper', 'epipelagic', 'photic'],
                'deep': ['deep', 'abyssal', 'bottom', 'benthic', 'bathypelagic'],
                'thermocline': ['thermocline', 'pycnocline', 'halocline', 'gradient']
            }
        }

        # Initialize TF-IDF for semantic understanding
        self.tfidf = TfidfVectorizer(stop_words='english', max_features=1000)
        self._build_domain_knowledge()

    def _build_domain_knowledge(self):
        """Build domain-specific knowledge base"""
        self.research_patterns = {
            'water_mass_analysis': [
                'water mass', 'water masses', 't-s diagram', 'temperature salinity',
                'antarctic', 'arctic', 'intermediate water', 'deep water'
            ],
            'climate_research': [
                'climate change', 'warming', 'trend', 'long term', 'variability',
                'el nino', 'la nina', 'monsoon', 'seasonal cycle'
            ],
            'physical_oceanography': [
                'circulation', 'current', 'upwelling', 'downwelling', 'mixing',
                'stratification', 'convection', 'advection'
            ],
            'marine_ecosystem': [
                'ecosystem', 'productivity', 'phytoplankton', 'chlorophyll',
                'nutrients', 'food chain', 'biogeochemical'
            ]
        }

    def enhance_query(self, query: str) -> QueryEnhancement:
        """Main query enhancement engine"""
        query_lower = query.lower()

        # Determine query intent and complexity
        intent = self._classify_query_intent(query_lower)
        complexity = self._assess_complexity(query_lower)

        # Extract requirements
        required_analysis = self._identify_required_analysis(query_lower)
        data_requirements = self._extract_data_requirements(query_lower)
        suggested_parameters = self._suggest_parameters(query_lower, intent)

        # Enhanced filtering
        enhanced_filters = self._create_enhanced_filters(query_lower, data_requirements)

        # Calculate confidence
        confidence = self._calculate_confidence(query_lower, intent, required_analysis)

        return QueryEnhancement(
            original_query=query,
            intent=intent,
            complexity_level=complexity,
            required_analysis=required_analysis,
            data_requirements=data_requirements,
            suggested_parameters=suggested_parameters,
            confidence_score=confidence,
            enhanced_filters=enhanced_filters
        )

    def _classify_query_intent(self, query: str) -> str:
        """Classify the primary intent of the query"""
        # Research-level classification
        if any(pattern in query for patterns in self.research_patterns.values() for pattern in patterns):
            if any(pattern in query for pattern in self.research_patterns['water_mass_analysis']):
                return 'water_mass_research'
            elif any(pattern in query for pattern in self.research_patterns['climate_research']):
                return 'climate_research'
            elif any(pattern in query for pattern in self.research_patterns['physical_oceanography']):
                return 'physical_oceanography'
            elif any(pattern in query for pattern in self.research_patterns['marine_ecosystem']):
                return 'marine_ecosystem_research'

        # Analysis-level classification
        for analysis_type, keywords in self.domain_vocabulary['analysis_types'].items():
            if any(keyword in query for keyword in keywords):
                return f'{analysis_type}_analysis'

        # Default to exploratory
        return 'exploratory_analysis'

    def _assess_complexity(self, query: str) -> str:
        """Assess query complexity based on multiple factors"""
        complexity_indicators = {
            'simple': 0,
            'intermediate': 0,
            'complex': 0,
            'research': 0
        }

        # Count complexity indicators
        # Simple indicators
        simple_patterns = ['show', 'what', 'find', 'get', 'temperature', 'salinity']
        complexity_indicators['simple'] += sum(1 for pattern in simple_patterns if pattern in query)

        # Intermediate indicators
        intermediate_patterns = ['compare', 'analyze', 'pattern', 'trend', 'correlation', 'distribution']
        complexity_indicators['intermediate'] += sum(1 for pattern in intermediate_patterns if pattern in query)

        # Complex indicators
        complex_patterns = ['anomaly', 'statistical', 'regression', 'model', 'prediction', 'cluster']
        complexity_indicators['complex'] += sum(1 for pattern in complex_patterns if pattern in query)

        # Research indicators
        research_patterns = ['water mass', 'thermohaline', 'geostrophic', 'baroclinic', 'pycnocline']
        complexity_indicators['research'] += sum(1 for pattern in research_patterns if pattern in query)

        # Multiple parameters/regions indicate complexity
        param_count = sum(1 for params in self.domain_vocabulary['parameters'].values()
                         for param in params if param in query)
        region_count = sum(1 for regions in self.domain_vocabulary['regions'].values()
                          for region in regions if region in query)

        if param_count > 2 or region_count > 1:
            complexity_indicators['complex'] += 2

        # Mathematical operations indicate complexity
        math_patterns = ['average', 'mean', 'difference', 'ratio', 'gradient', 'derivative']
        if any(pattern in query for pattern in math_patterns):
            complexity_indicators['complex'] += 1

        # Depth specifications add complexity
        depth_specs = re.findall(r'\d+\s*m(?:eter)?s?', query)
        if len(depth_specs) > 1:
            complexity_indicators['intermediate'] += 1

        # Return highest scoring complexity
        return max(complexity_indicators, key=complexity_indicators.get)

    def _identify_required_analysis(self, query: str) -> List[str]:
        """Identify what types of analysis are needed"""
        required_analysis = []

        analysis_mapping = {
            'statistical_analysis': ['statistics', 'statistical', 'mean', 'average', 'std', 'distribution'],
            'anomaly_detection': ['anomaly', 'outlier', 'unusual', 'abnormal', 'strange'],
            'time_series_analysis': ['trend', 'time series', 'temporal', 'seasonal', 'annual'],
            'comparative_analysis': ['compare', 'comparison', 'versus', 'between', 'difference'],
            'spatial_analysis': ['spatial', 'geographic', 'region', 'area', 'map'],
            'depth_profile_analysis': ['profile', 'depth', 'vertical', 'thermocline'],
            'correlation_analysis': ['correlation', 'relationship', 'associated'],
            'clustering_analysis': ['cluster', 'group', 'similar', 'pattern', 'classification'],
            'quality_assessment': ['quality', 'validate', 'check', 'error', 'accuracy']
        }

        for analysis_type, keywords in analysis_mapping.items():
            if any(keyword in query for keyword in keywords):
                required_analysis.append(analysis_type)

        # Default analysis based on query characteristics
        if not required_analysis:
            if any(word in query for word in ['what', 'show', 'find']):
                required_analysis.append('exploratory_analysis')

        return required_analysis

    def _extract_data_requirements(self, query: str) -> Dict[str, any]:
        """Extract specific data requirements from query"""
        requirements = {
            'parameters': [],
            'regions': [],
            'depth_range': None,
            'time_range': None,
            'quality_level': 'standard',
            'sample_size': 'adaptive'
        }

        # Extract parameters
        for param, keywords in self.domain_vocabulary['parameters'].items():
            if any(keyword in query for keyword in keywords):
                requirements['parameters'].append(param)

        # Extract regions
        for region, keywords in self.domain_vocabulary['regions'].items():
            if any(keyword in query for keyword in keywords):
                requirements['regions'].append(region)

        # Extract depth requirements
        depth_patterns = [
            r'below (\d+)\s*m',
            r'above (\d+)\s*m',
            r'depth.*?(\d+).*?(\d+)',
            r'(\d+)\s*(?:to|-)\s*(\d+)\s*m'
        ]

        for pattern in depth_patterns:
            match = re.search(pattern, query)
            if match:
                if len(match.groups()) == 1:
                    depth_value = float(match.group(1))
                    if 'below' in pattern:
                        requirements['depth_range'] = {'min': depth_value, 'max': None}
                    elif 'above' in pattern:
                        requirements['depth_range'] = {'min': None, 'max': depth_value}
                elif len(match.groups()) == 2:
                    requirements['depth_range'] = {
                        'min': float(match.group(1)),
                        'max': float(match.group(2))
                    }
                break

        # Extract quality requirements
        if any(word in query for word in ['research', 'publication', 'scientific', 'accurate']):
            requirements['quality_level'] = 'high'
        elif any(word in query for word in ['quick', 'overview', 'rough', 'approximate']):
            requirements['quality_level'] = 'fast'

        # Extract sample size preferences
        if any(word in query for word in ['comprehensive', 'complete', 'all', 'entire', 'full']):
            requirements['sample_size'] = 'comprehensive'
        elif any(word in query for word in ['sample', 'example', 'few', 'some']):
            requirements['sample_size'] = 'sample'

        return requirements

    def _suggest_parameters(self, query: str, intent: str) -> List[str]:
        """Suggest additional parameters that might be relevant"""
        suggested = []

        # Intent-based suggestions
        if intent == 'water_mass_research':
            suggested.extend(['temperature', 'salinity', 'density', 'pressure'])
        elif intent == 'climate_research':
            suggested.extend(['temperature', 'heat_content', 'sea_level'])
        elif 'anomaly' in intent:
            suggested.extend(['temperature', 'salinity', 'chlorophyll'])

        # Query content suggestions
        if 'temperature' in query and 'salinity' not in query:
            suggested.append('salinity')  # T-S analysis potential
        if 'depth' in query and 'pressure' not in query:
            suggested.append('pressure')  # Depth-pressure relationship

        # Remove duplicates and already mentioned parameters
        mentioned_params = []
        for param, keywords in self.domain_vocabulary['parameters'].items():
            if any(keyword in query for keyword in keywords):
                mentioned_params.append(param)

        suggested = list(set(suggested) - set(mentioned_params))
        return suggested[:3]  # Top 3 suggestions

    def _create_enhanced_filters(self, query: str, data_requirements: Dict) -> Dict[str, any]:
        """Create enhanced filtering criteria"""
        enhanced_filters = {}

        # Parameter-specific filters
        if 'temperature' in data_requirements['parameters']:
            temp_filters = self._extract_temperature_criteria(query)
            if temp_filters:
                enhanced_filters['temperature'] = temp_filters

        if 'salinity' in data_requirements['parameters']:
            salinity_filters = self._extract_salinity_criteria(query)
            if salinity_filters:
                enhanced_filters['salinity'] = salinity_filters

        # Depth filters
        if data_requirements['depth_range']:
            enhanced_filters['depth'] = data_requirements['depth_range']

        # Quality filters
        if data_requirements['quality_level'] == 'high':
            enhanced_filters['quality_control'] = {
                'remove_outliers': True,
                'minimum_measurements_per_profile': 5,
                'data_flags': 'good_only'
            }

        # Spatial filters based on research requirements
        if any(region in query for region in ['frontal', 'eddy', 'gyre']):
            enhanced_filters['spatial_features'] = True

        return enhanced_filters

    def _extract_temperature_criteria(self, query: str) -> Optional[Dict]:
        """Extract temperature-specific criteria"""
        # Temperature thresholds
        temp_patterns = [
            r'temperature\s*(?:above|over|greater than|>)\s*(\d+(?:\.\d+)?)',
            r'temperature\s*(?:below|under|less than|<)\s*(\d+(?:\.\d+)?)',
            r'warm(?:er)?\s*than\s*(\d+(?:\.\d+)?)',
            r'cold(?:er)?\s*than\s*(\d+(?:\.\d+)?)'
        ]

        for pattern in temp_patterns:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                value = float(match.group(1))
                if 'above' in pattern or 'greater' in pattern or '>' in pattern or 'warm' in pattern:
                    return {'operator': '>', 'value': value}
                elif 'below' in pattern or 'less' in pattern or '<' in pattern or 'cold' in pattern:
                    return {'operator': '<', 'value': value}

        return None

    def _extract_salinity_criteria(self, query: str) -> Optional[Dict]:
        """Extract salinity-specific criteria"""
        # Salinity characteristics
        if 'high salinity' in query:
            return {'operator': '>', 'value': 35.0}
        elif 'low salinity' in query:
            return {'operator': '<', 'value': 34.0}
        elif 'fresh' in query:
            return {'operator': '<', 'value': 32.0}

        return None

    def _calculate_confidence(self, query: str, intent: str, required_analysis: List[str]) -> float:
        """Calculate confidence in query understanding"""
        confidence = 0.5  # Base confidence

        # Intent clarity
        if intent != 'exploratory_analysis':
            confidence += 0.2

        # Specific parameters mentioned
        param_mentions = sum(1 for params in self.domain_vocabulary['parameters'].values()
                           for param in params if param in query)
        confidence += min(param_mentions * 0.1, 0.3)

        # Clear analysis requirements
        if required_analysis:
            confidence += min(len(required_analysis) * 0.1, 0.3)

        # Specific regions mentioned
        region_mentions = sum(1 for regions in self.domain_vocabulary['regions'].values()
                            for region in regions if region in query)
        if region_mentions > 0:
            confidence += 0.1

        # Mathematical/quantitative terms
        quant_terms = ['average', 'mean', 'difference', 'compare', 'analyze', 'correlation']
        quant_mentions = sum(1 for term in quant_terms if term in query)
        if quant_mentions > 0:
            confidence += 0.1

        return min(confidence, 1.0)

    def optimize_data_retrieval(self, enhancement: QueryEnhancement) -> Dict[str, any]:
        """Optimize data retrieval strategy based on query enhancement"""
        optimization = {
            'sample_strategy': 'adaptive',
            'minimum_points': 30,
            'geographic_spread': True,
            'temporal_coverage': False,
            'quality_priority': 'balanced'
        }

        # Adjust based on complexity
        if enhancement.complexity_level == 'research':
            optimization['minimum_points'] = 500
            optimization['quality_priority'] = 'high'
            optimization['temporal_coverage'] = True

        elif enhancement.complexity_level == 'complex':
            optimization['minimum_points'] = 200
            optimization['sample_strategy'] = 'stratified'

        # Adjust based on intent
        if 'comparative' in enhancement.intent:
            optimization['geographic_spread'] = True
            optimization['minimum_points_per_group'] = 50

        elif 'anomaly' in enhancement.intent:
            optimization['quality_priority'] = 'high'
            optimization['outlier_inclusion'] = True

        # Adjust based on required analysis
        if 'time_series_analysis' in enhancement.required_analysis:
            optimization['temporal_coverage'] = True
            optimization['minimum_time_span'] = '6_months'

        if 'statistical_analysis' in enhancement.required_analysis:
            optimization['minimum_points'] = max(optimization['minimum_points'], 100)

        return optimization
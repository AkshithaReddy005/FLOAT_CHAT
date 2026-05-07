"""
Universal Operator Parser
Handles mathematical operators in any format: >, <, >=, <=, =, !=
"""

import re
from typing import Optional, Tuple, Dict, Any, List

class UniversalOperatorParser:
    """Universal parser for mathematical operators and parameters"""
    
    def __init__(self):
        # Mathematical operators (all possible formats)
        self.operators = {
            '>': ('>', 'greater_than'),
            '<': ('<', 'less_than'),
            '>=': ('>=', 'greater_equal'),
            '<=': ('<=', 'less_equal'),
            '=': ('=', 'equal'),
            '==': ('=', 'equal'),
            '!=': ('!=', 'not_equal'),
            'gt': ('>', 'greater_than'),
            'lt': ('<', 'less_than'),
            'ge': ('>=', 'greater_equal'),
            'le': ('<=', 'less_equal'),
            'eq': ('=', 'equal'),
            'ne': ('!=', 'not_equal')
        }
        
        # Parameter keywords (case-insensitive)
        self.parameter_keywords = {
            'depth': ['depth', 'dpth', 'deph', 'dept', 'deth', 'deep'],
            'temperature': ['temperature', 'temp', 'temprature', 'tempr', 'tmp', 'celsius', 'c'],
            'salinity': ['salinity', 'sal', 'salinty', 'salnity', 'slinity', 'salt']
        }
        
        # Universal patterns - catch ANY parameter with ANY operator
        self.universal_patterns = [
            # Mathematical operator patterns (most flexible)
            r'(\w+)\s*([><=!]=?|==|!=)\s*(\d+(?:\.\d+)?)',
            r'(\w+)\s+(gt|lt|ge|le|eq|ne)\s+(\d+(?:\.\d+)?)',
            
            # Word-based patterns (fallback)
            r'(\w+)\s+(greater than|more than|above|over|less than|below|under|equal to|equals?|not equal to)\s+(\d+(?:\.\d+)?)',
            
            # Context patterns
            r'(\w+)\s+is\s+(greater than|more than|above|over|less than|below|under|equal to|equals?|not equal to)\s+(\d+(?:\.\d+)?)',
            r'where\s+(\w+)\s+(greater than|more than|above|over|less than|below|under|equal to|equals?|not equal to)\s+(\d+(?:\.\d+)?)',
        ]
    
    def normalize_operator(self, operator_str: str) -> Optional[str]:
        """Normalize any operator format to standard SQL operator"""
        operator_str = operator_str.strip()
        
        # Direct match
        if operator_str in self.operators:
            return self.operators[operator_str][0]
        
        # Word-based conversion
        word_to_operator = {
            'greater than': '>',
            'more than': '>',
            'above': '>',
            'over': '>',
            'less than': '<',
            'below': '<',
            'under': '<',
            'equal to': '=',
            'equals': '=',
            'equal': '=',
            'not equal to': '!=',
            'not equal': '!='
        }
        
        return word_to_operator.get(operator_str.lower())
    
    def identify_parameter(self, param_word: str) -> Optional[str]:
        """Identify parameter type from keyword"""
        param_word = param_word.lower()
        
        for param_type, keywords in self.parameter_keywords.items():
            if param_word in keywords:
                return param_type
        
        # Fuzzy matching for typos
        for param_type, keywords in self.parameter_keywords.items():
            for keyword in keywords:
                if self._fuzzy_match(param_word, keyword, threshold=0.7):
                    return param_type
        
        return None
    
    def _fuzzy_match(self, text: str, target: str, threshold: float = 0.7) -> bool:
        """Simple fuzzy matching"""
        from difflib import SequenceMatcher
        similarity = SequenceMatcher(None, text.lower(), target.lower()).ratio()
        return similarity >= threshold
    
    def parse_universal_expression(self, query: str) -> Dict[str, Any]:
        """Parse any mathematical expression in the query"""
        results = {
            'expressions': [],
            'parameters_found': []
        }
        
        query_lower = query.lower()
        
        for pattern in self.universal_patterns:
            matches = re.finditer(pattern, query_lower, re.IGNORECASE)
            
            for match in matches:
                if len(match.groups()) == 3:
                    param_word, operator_str, value_str = match.groups()
                    
                    # Normalize operator
                    operator = self.normalize_operator(operator_str)
                    if not operator:
                        continue
                    
                    # Identify parameter
                    param_type = self.identify_parameter(param_word)
                    if not param_type:
                        continue
                    
                    # Parse value
                    try:
                        value = float(value_str)
                    except ValueError:
                        continue
                    
                    expression = {
                        'parameter': param_type,
                        'operator': operator,
                        'value': value,
                        'raw_text': match.group(0),
                        'confidence': 0.9
                    }
                    
                    results['expressions'].append(expression)
                    if param_type not in results['parameters_found']:
                        results['parameters_found'].append(param_type)
        
        return results
    
    def extract_parameters_universal(self, query: str) -> Dict[str, Any]:
        """Extract parameters using universal parsing"""
        parsed = self.parse_universal_expression(query)
        
        result = {
            'depth_range': None,
            'depth_type': None,
            'temperature_range': None,
            'salinity_range': None,
            'expressions': parsed['expressions'],
            'confidence_scores': {}
        }
        
        # Process expressions
        for expr in parsed['expressions']:
            param_type = expr['parameter']
            operator = expr['operator']
            value = expr['value']
            confidence = expr['confidence']
            
            if param_type == 'depth':
                result['depth_range'] = (operator, value)
                result['depth_type'] = 'operator'
                result['confidence_scores']['depth'] = confidence
            elif param_type == 'temperature':
                result['temperature_range'] = (operator, value)
                result['confidence_scores']['temperature'] = confidence
            elif param_type == 'salinity':
                result['salinity_range'] = (operator, value)
                result['confidence_scores']['salinity'] = confidence
        
        return result
    
    def demonstrate_universal_parsing(self, queries: List[str]):
        """Demonstrate universal parsing capabilities"""
        print("=== Universal Operator Parser Demo ===")
        
        for query in queries:
            print(f"\nQuery: '{query}'")
            params = self.extract_parameters_universal(query)
            
            if params['expressions']:
                print(f"  Found {len(params['expressions'])} expression(s):")
                for expr in params['expressions']:
                    print(f"    {expr['parameter']} {expr['operator']} {expr['value']} (confidence: {expr['confidence']})")
                
                if params['depth_range']:
                    print(f"  Depth: {params['depth_range']}")
                if params['temperature_range']:
                    print(f"  Temperature: {params['temperature_range']}")
                if params['salinity_range']:
                    print(f"  Salinity: {params['salinity_range']}")
            else:
                print("  No expressions found")

# Test the universal parser
if __name__ == "__main__":
    parser = UniversalOperatorParser()
    
    test_queries = [
        "depth>500 in indian ocean",
        "temp<25 degrees",
        "salinity>=35",
        "temperature > 30 and depth < 1000",
        "where salinity != 34.5",
        "depth >= 200 meters",
        "temp <= 15 celsius",
        "depth=500",
        "temperature==25",
        "salinity ne 35",
        "depth gt 1000",
        "temp lt 10",
        "dpth > 500",  # typo
        "temprature < 30",  # typo
    ]
    
    parser.demonstrate_universal_parsing(test_queries)

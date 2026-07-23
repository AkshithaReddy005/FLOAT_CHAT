export interface TestCase {
  query: string;
  expectedType: string;
}

export interface TestSuite {
  id: string;
  name: string;
  description: string;
  queries: TestCase[];
}

export const testSuites: TestSuite[] = [
  {
    id: 'temperature',
    name: 'Temperature Queries',
    description: 'Evaluates temperature profiles, thresholds, averages, and horizontal comparisons.',
    queries: [
      { query: 'Show me temperature profiles near Mumbai', expectedType: 'profile_analysis' },
      { query: 'Find measurements with temperature above 28 degrees', expectedType: 'profile_analysis' },
      { query: 'What is the average temperature in the Arabian Sea?', expectedType: 'exploratory_analysis' },
      { query: 'Compare temperature profiles in Bay of Bengal vs Arabian Sea', expectedType: 'exploratory_analysis' },
      { query: 'Show temperature variations in the surface layers', expectedType: 'profile_analysis' },
      { query: 'Show deep water temperature measurements', expectedType: 'profile_analysis' },
      { query: 'Find temperature profile for float 2901234', expectedType: 'profile_analysis' },
      { query: 'Compare surface temperature vs deep temperature in Indian Ocean', expectedType: 'exploratory_analysis' }
    ]
  },
  {
    id: 'salinity',
    name: 'Salinity Queries',
    description: 'Evaluates salinity ranges, averages, maps, and specific regional dynamics.',
    queries: [
      { query: 'Show salinity patterns in the Indian Ocean', expectedType: 'exploratory_analysis' },
      { query: 'Find measurements with salinity below 34 psu', expectedType: 'profile_analysis' },
      { query: 'What is the maximum salinity in the Bay of Bengal?', expectedType: 'exploratory_analysis' },
      { query: 'Compare salinity between Arabian Sea and Bay of Bengal', expectedType: 'exploratory_analysis' },
      { query: 'Show salinity profiles near Chennai', expectedType: 'profile_analysis' },
      { query: 'Salinity profile for float 2901234 in 2023', expectedType: 'profile_analysis' },
      { query: 'Average salinity at depths below 500 meters', expectedType: 'exploratory_analysis' },
      { query: 'Show surface salinity near Mumbai in summer', expectedType: 'profile_analysis' }
    ]
  },
  {
    id: 'float_search',
    name: 'Float Search Queries',
    description: 'Tests float identifier searches, trajectory visualizer, and instrument parameters.',
    queries: [
      { query: 'Find observations from Float 2901234', expectedType: 'profile_analysis' },
      { query: 'Show measurements for float 1901322', expectedType: 'profile_analysis' },
      { query: 'What parameters does float 2901234 measure?', expectedType: 'exploratory_analysis' },
      { query: 'Show the trajectory map of float 2901234', expectedType: 'profile_analysis' },
      { query: 'Find all records for float 2901234 under 200m depth', expectedType: 'profile_analysis' },
      { query: 'Show temperature timeline for float 1901322', expectedType: 'profile_analysis' },
      { query: 'Find coordinates of float 2901234 in March 2023', expectedType: 'profile_analysis' },
      { query: 'Compare salinity between float 2901234 and float 1901322', expectedType: 'exploratory_analysis' }
    ]
  },
  {
    id: 'spatial_regional',
    name: 'Spatial & Regional Queries',
    description: 'Tests coordinate bounding boxes, local and global seas, and distance metrics.',
    queries: [
      { query: 'What data do we have for the Arabian Sea?', expectedType: 'exploratory_analysis' },
      { query: 'Show measurements near Chennai', expectedType: 'profile_analysis' },
      { query: 'Find observations in the Southern Indian Ocean', expectedType: 'exploratory_analysis' },
      { query: 'Show temperature profiles in the Bay of Bengal', expectedType: 'profile_analysis' },
      { query: 'What floats are currently active near Mumbai?', expectedType: 'profile_analysis' },
      { query: 'Get observations within 200km of Sri Lanka', expectedType: 'profile_analysis' },
      { query: 'Show salinity patterns in the Equatorial Indian Ocean', expectedType: 'exploratory_analysis' },
      { query: 'Compare data coverage between Arabian Sea and Indian Ocean', expectedType: 'exploratory_analysis' }
    ]
  },
  {
    id: 'multi_turn',
    name: 'Multi-turn & Context Queries',
    description: 'Verifies the Conversation Summary Memory, checking reference resolutions and context continuation.',
    queries: [
      { query: 'Show salinity profiles near Chennai', expectedType: 'profile_analysis' },
      { query: 'Compare it with the Arabian Sea', expectedType: 'exploratory_analysis' },
      { query: 'Show measurements for float 2901234', expectedType: 'profile_analysis' },
      { query: 'What is the average temperature for this float?', expectedType: 'exploratory_analysis' },
      { query: 'Filter these results to depths above 100 meters', expectedType: 'profile_analysis' },
      { query: 'Now compare it with float 1901322', expectedType: 'exploratory_analysis' },
      { query: 'Show the salinity profile instead', expectedType: 'profile_analysis' },
      { query: 'Summarize all measurements we just discussed', expectedType: 'exploratory_analysis' }
    ]
  },
  {
    id: 'edge_cases',
    name: 'Edge Cases & Error Handling',
    description: 'Tests limits, boundary violations, unphysical values, and out-of-domain queries.',
    queries: [
      { query: 'Show measurements from the year 1850', expectedType: 'profile_analysis' },
      { query: 'Find measurements at depth 50000 meters', expectedType: 'profile_analysis' },
      { query: 'What is the temperature at latitude 100?', expectedType: 'profile_analysis' },
      { query: 'Find float ID INVALID_FLOAT', expectedType: 'profile_analysis' },
      { query: 'Show temperature in the Sahara Desert', expectedType: 'profile_analysis' },
      { query: 'Find measurements with salinity above 100 psu', expectedType: 'profile_analysis' },
      { query: 'Show data for March 2035', expectedType: 'profile_analysis' },
      { query: 'Show me the price of apples', expectedType: 'exploratory_analysis' }
    ]
  }
];

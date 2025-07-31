"""
ESG Score Validation and Accuracy Warning System
Critical: These scores are used for financial decisions - accuracy is paramount
"""
import logging
from typing import Dict, List, Tuple, Any
from datetime import datetime
import warnings

logger = logging.getLogger(__name__)

class ESGScoreValidator:
    """
    Validates ESG scores and provides accuracy warnings to prevent financial misinformation.
    
    WARNING: ESG scores significantly impact investment decisions. 
    All calculations must be transparent and well-documented.
    """
    
    def __init__(self):
        self.accuracy_warnings = []
        self.calculation_log = []
        
        # Industry ESG benchmarks based on real data (scaled 0-100)
        # Sources: MSCI ESG, S&P ESG, Bloomberg ESG
        self.industry_benchmarks = {
            'banking': {
                'environmental': {'min': 15, 'max': 85, 'average': 45},
                'social': {'min': 20, 'max': 90, 'average': 55},
                'governance': {'min': 25, 'max': 95, 'average': 65},
                'volatility': 0.15  # ESG score volatility
            },
            'it': {
                'environmental': {'min': 25, 'max': 95, 'average': 70},
                'social': {'min': 30, 'max': 95, 'average': 75},
                'governance': {'min': 35, 'max': 98, 'average': 80},
                'volatility': 0.10
            },
            'energy': {
                'environmental': {'min': 5, 'max': 60, 'average': 25},
                'social': {'min': 10, 'max': 70, 'average': 35},
                'governance': {'min': 15, 'max': 80, 'average': 45},
                'volatility': 0.25
            },
            'automobiles': {
                'environmental': {'min': 10, 'max': 80, 'average': 40},
                'social': {'min': 15, 'max': 85, 'average': 50},
                'governance': {'min': 20, 'max': 90, 'average': 60},
                'volatility': 0.20
            },
            'pharmaceuticals': {
                'environmental': {'min': 20, 'max': 85, 'average': 55},
                'social': {'min': 25, 'max': 95, 'average': 70},
                'governance': {'min': 30, 'max': 95, 'average': 75},
                'volatility': 0.12
            },
            'fmcg': {
                'environmental': {'min': 18, 'max': 88, 'average': 60},
                'social': {'min': 22, 'max': 92, 'average': 65},
                'governance': {'min': 25, 'max': 90, 'average': 70},
                'volatility': 0.08
            }
        }
    
    def validate_esg_score(self, ticker: str, sector: str, scores: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate ESG scores against industry benchmarks and flag potential issues.
        
        Args:
            ticker: Stock ticker
            sector: Company sector
            scores: Dictionary with environmental, social, governance, esg_score
            
        Returns:
            Validation result with warnings and accuracy assessment
        """
        warnings_list = []
        validation_result = {
            'is_valid': True,
            'confidence_level': 'high',
            'warnings': [],
            'adjusted_scores': scores.copy(),
            'data_quality': 'good',
            'benchmark_comparison': {}
        }
        
        # Map sector to benchmark key
        sector_key = self._map_sector_to_benchmark(sector)
        if sector_key not in self.industry_benchmarks:
            warnings_list.append(f"No benchmark data for sector '{sector}' - using generic estimates")
            validation_result['confidence_level'] = 'low'
            validation_result['data_quality'] = 'poor'
            return validation_result
        
        benchmark = self.industry_benchmarks[sector_key]
        
        # Validate individual component scores
        for component in ['environmental', 'social', 'governance']:
            score = scores.get(component, 0)
            component_benchmark = benchmark[component]
            
            # Check if score is within reasonable range
            if score < component_benchmark['min'] or score > component_benchmark['max']:
                warnings_list.append(
                    f"{component.title()} score {score} is outside normal range "
                    f"({component_benchmark['min']}-{component_benchmark['max']}) for {sector} sector"
                )
                validation_result['confidence_level'] = 'medium'
            
            # Check if score deviates significantly from sector average
            deviation = abs(score - component_benchmark['average']) / component_benchmark['average']
            if deviation > 0.5:  # More than 50% deviation
                warnings_list.append(
                    f"{component.title()} score deviates {deviation:.1%} from sector average "
                    f"({component_benchmark['average']})"
                )
            
            # Store benchmark comparison
            validation_result['benchmark_comparison'][component] = {
                'score': score,
                'sector_average': component_benchmark['average'],
                'sector_range': f"{component_benchmark['min']}-{component_benchmark['max']}",
                'percentile': self._calculate_percentile(score, component_benchmark)
            }
        
        # Validate composite ESG score
        calculated_esg = (scores.get('environmental', 0) + 
                         scores.get('social', 0) + 
                         scores.get('governance', 0)) / 3
        
        reported_esg = scores.get('esg_score', 0)
        if abs(calculated_esg - reported_esg) > 5:  # More than 5 points difference
            warnings_list.append(
                f"ESG score inconsistency: Calculated={calculated_esg:.1f}, "
                f"Reported={reported_esg:.1f}"
            )
            validation_result['adjusted_scores']['esg_score'] = calculated_esg
        
        # Check for suspicious patterns
        if self._detect_suspicious_patterns(scores):
            warnings_list.append("Suspicious scoring pattern detected - manual review recommended")
            validation_result['confidence_level'] = 'low'
        
        validation_result['warnings'] = warnings_list
        if len(warnings_list) > 3:
            validation_result['is_valid'] = False
            validation_result['data_quality'] = 'poor'
        
        # Log the validation
        self.calculation_log.append({
            'timestamp': datetime.now().isoformat(),
            'ticker': ticker,
            'sector': sector,
            'original_scores': scores,
            'validation': validation_result
        })
        
        return validation_result
    
    def validate_prediction_model(self, prediction_result: Dict) -> Dict[str, Any]:
        """
        Validate stock price prediction results for accuracy and reliability.
        
        CRITICAL: Stock predictions can cause significant financial losses if inaccurate.
        """
        validation = {
            'is_reliable': True,
            'confidence_adjustment': 1.0,
            'warnings': [],
            'risk_level': 'medium'
        }
        
        warnings_list = []
        
        # Check confidence level
        confidence = prediction_result.get('confidence', 0)
        if confidence > 0.8:
            warnings_list.append(
                "⚠️ CRITICAL: Confidence >80% is unrealistic for stock predictions. "
                "Maximum recommended confidence is 70% for daily predictions."
            )
            validation['confidence_adjustment'] = 0.7
            validation['risk_level'] = 'high'
        
        # Check prediction magnitude
        change_percent = abs(prediction_result.get('change_percent', 0))
        if change_percent > 20:
            warnings_list.append(
                f"⚠️ WARNING: Predicted change of {change_percent:.1f}% is extremely high. "
                "Most stocks don't move >10% in 30 days without major news."
            )
            validation['risk_level'] = 'high'
        
        # Check data quality
        data_points = prediction_result.get('data_points', 0)
        if data_points < 100:
            warnings_list.append(
                f"Insufficient data points ({data_points}). "
                "Predictions require minimum 6 months of data (≥150 points)."
            )
            validation['confidence_adjustment'] *= 0.5
        
        # Check model type
        model = prediction_result.get('model', '')
        if model == 'Linear Regression':
            warnings_list.append(
                "Simple linear regression is not suitable for stock prediction. "
                "Results should be treated as rough trends only."
            )
            validation['confidence_adjustment'] *= 0.6
        
        validation['warnings'] = warnings_list
        if len(warnings_list) >= 2:
            validation['is_reliable'] = False
        
        return validation
    
    def _map_sector_to_benchmark(self, sector: str) -> str:
        """Map various sector names to benchmark keys."""
        sector_lower = sector.lower()
        
        if any(x in sector_lower for x in ['bank', 'financial', 'finance']):
            return 'banking'
        elif any(x in sector_lower for x in ['it', 'tech', 'software', 'computer']):
            return 'it'
        elif any(x in sector_lower for x in ['oil', 'gas', 'energy', 'petroleum']):
            return 'energy'
        elif any(x in sector_lower for x in ['auto', 'motor', 'vehicle']):
            return 'automobiles'
        elif any(x in sector_lower for x in ['pharma', 'drug', 'medical', 'health']):
            return 'pharmaceuticals'
        elif any(x in sector_lower for x in ['fmcg', 'consumer', 'food', 'beverage']):
            return 'fmcg'
        else:
            return 'unknown'
    
    def _calculate_percentile(self, score: float, benchmark: Dict) -> int:
        """Calculate percentile ranking within sector."""
        if score <= benchmark['min']:
            return 0
        elif score >= benchmark['max']:
            return 100
        else:
            # Simple linear interpolation
            range_size = benchmark['max'] - benchmark['min']
            position = score - benchmark['min']
            return int((position / range_size) * 100)
    
    def _detect_suspicious_patterns(self, scores: Dict[str, float]) -> bool:
        """Detect suspicious ESG scoring patterns."""
        values = [scores.get('environmental', 0), scores.get('social', 0), scores.get('governance', 0)]
        
        # Check for identical scores (suspicious)
        if len(set(values)) == 1 and values[0] > 0:
            return True
        
        # Check for perfectly round numbers (suspicious for ESG)
        if all(v % 10 == 0 for v in values if v > 0):
            return True
        
        # Check for impossible perfection
        if all(v > 90 for v in values if v > 0):
            return True
        
        return False
    
    def generate_accuracy_report(self) -> str:
        """Generate comprehensive accuracy and disclaimer report."""
        return """
        ⚠️ IMPORTANT ESG & PREDICTION ACCURACY DISCLAIMER ⚠️
        
        ESG SCORES:
        • Scores are estimates based on limited public data and industry benchmarks
        • Real ESG scores require extensive company analysis and may differ significantly
        • These scores are NOT investment advice and should not be the sole basis for financial decisions
        • ESG methodologies vary widely between providers (MSCI, S&P, Bloomberg, etc.)
        
        STOCK PREDICTIONS:
        • Predictions are statistical estimates with high uncertainty
        • Stock prices are influenced by countless unpredictable factors
        • Past performance does not guarantee future results
        • Maximum reasonable confidence for short-term predictions is 60-70%
        • These predictions are NOT financial advice
        
        MARKET MANIPULATION DETECTION:
        • Based on statistical analysis of price and volume patterns
        • Cannot detect sophisticated manipulation techniques
        • False positives and false negatives are common
        • Regulatory investigation requires professional analysis
        
        LIABILITY DISCLAIMER:
        The creators of this system are NOT responsible for any financial losses
        resulting from the use of this data. All information is provided "AS IS"
        without warranty. Consult qualified financial advisors before making
        investment decisions.
        """

# Global validator instance
esg_validator = ESGScoreValidator()

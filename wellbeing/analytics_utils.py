"""
Advanced analytics utilities for wellbeing data analysis.
Includes segmentation, correlations, predictions, and heatmap generation.
"""

from django.db.models import Avg, Count, Q
from datetime import timedelta
from django.utils import timezone
import statistics
from .models import WellbeingRecord

# ✅ CORRECT: Import au niveau du module
from django.contrib.auth import get_user_model
User = get_user_model()


class UserSegmentation:
    """Categorize users based on their wellbeing metrics."""
    
    SEGMENTS = {
        'CRITICAL': {'label': 'Critical', 'color': '#dc2626', 'icon': '⚠️'},
        'AT_RISK': {'label': 'At Risk', 'color': '#f97316', 'icon': '⚡'},
        'NORMAL': {'label': 'Normal', 'color': '#eab308', 'icon': '→'},
        'EXCELLENT': {'label': 'Excellent', 'color': '#22c55e', 'icon': '✓'},
    }
    
    @staticmethod
    def get_user_segment(user, days=30):
        """
        Determine user segment based on recent wellbeing metrics.
        
        Segments:
        - CRITICAL: avg_mood < 3 OR avg_sleep < 4
        - AT_RISK: avg_mood < 5 OR avg_sleep < 6 OR declining trend
        - NORMAL: avg_mood 5-7 AND avg_sleep 6-8
        - EXCELLENT: avg_mood > 7 AND avg_sleep > 7
        """
        start_date = timezone.now().date() - timedelta(days=days)
        records = WellbeingRecord.objects.filter(
            user=user,
            date__gte=start_date
        ).order_by('date')
        
        if not records.exists():
            return 'NORMAL'
        
        avg_mood = records.aggregate(Avg('mood_score'))['mood_score__avg'] or 0
        avg_sleep = records.aggregate(Avg('sleep_hours'))['sleep_hours__avg'] or 0
        avg_energy = records.aggregate(Avg('energy_level'))['energy_level__avg'] or 0
        
        # Check for declining trend
        first_half = records[:len(records)//2]
        second_half = records[len(records)//2:]
        
        if first_half and second_half:
            first_avg = sum(r.mood_score for r in first_half) / len(first_half)
            second_avg = sum(r.mood_score for r in second_half) / len(second_half)
            is_declining = second_avg < first_avg - 1
        else:
            is_declining = False
        
        # Segmentation logic
        if avg_mood < 3 or avg_sleep < 4:
            return 'CRITICAL'
        elif avg_mood < 5 or avg_sleep < 6 or is_declining:
            return 'AT_RISK'
        elif avg_mood > 7 and avg_sleep > 7 and avg_energy > 7:
            return 'EXCELLENT'
        else:
            return 'NORMAL'
    
    @staticmethod
    def get_all_user_segments(days=30):
        """Get segmentation for all users."""
        # ✅ CORRIGÉ: wellbeing_records au lieu de wellbeingrecord
        users = User.objects.filter(wellbeing_records__isnull=False).distinct()
        segments = {}
        
        for user in users:
            segment = UserSegmentation.get_user_segment(user, days)
            if segment not in segments:
                segments[segment] = []
            segments[segment].append({
                'user': user,
                'username': user.username,
                'email': user.email,
            })
        
        return segments


class CorrelationAnalysis:
    """Calculate correlations between wellbeing variables."""
    
    @staticmethod
    def calculate_correlations(records):
        """
        Calculate Pearson correlation between variables.
        Returns correlation matrix.
        """
        if len(records) < 2:
            return {}
        
        # Extract data
        moods = [r.mood_score for r in records]
        energies = [r.energy_level for r in records]
        sleeps = [r.sleep_hours for r in records]
        productivities = [r.productivity_score for r in records]
        
        correlations = {
            'mood_vs_energy': CorrelationAnalysis._pearson_correlation(moods, energies),
            'mood_vs_sleep': CorrelationAnalysis._pearson_correlation(moods, sleeps),
            'mood_vs_productivity': CorrelationAnalysis._pearson_correlation(moods, productivities),
            'sleep_vs_energy': CorrelationAnalysis._pearson_correlation(sleeps, energies),
            'sleep_vs_productivity': CorrelationAnalysis._pearson_correlation(sleeps, productivities),
            'energy_vs_productivity': CorrelationAnalysis._pearson_correlation(energies, productivities),
        }
        
        return correlations
    
    @staticmethod
    def _pearson_correlation(x, y):
        """Calculate Pearson correlation coefficient."""
        if len(x) < 2 or len(y) < 2:
            return 0
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(y)
        
        numerator = sum((x[i] - mean_x) * (y[i] - mean_y) for i in range(len(x)))
        denominator = (
            (sum((xi - mean_x) ** 2 for xi in x) ** 0.5) *
            (sum((yi - mean_y) ** 2 for yi in y) ** 0.5)
        )
        
        if denominator == 0:
            return 0
        
        return round(numerator / denominator, 3)
    
    @staticmethod
    def get_correlation_insights(correlations):
        """Generate human-readable insights from correlations."""
        insights = []
        
        for key, value in correlations.items():
            if abs(value) > 0.7:
                strength = "strong"
            elif abs(value) > 0.4:
                strength = "moderate"
            else:
                strength = "weak"
            
            direction = "positive" if value > 0 else "negative"
            
            # Format key to readable text
            readable_key = key.replace('_', ' ').title()
            
            insights.append({
                'metric': readable_key,
                'correlation': value,
                'strength': strength,
                'direction': direction,
                'description': f"{strength.capitalize()} {direction} correlation"
            })
        
        return sorted(insights, key=lambda x: abs(x['correlation']), reverse=True)


class PredictiveTrends:
    """Identify users at risk based on trend analysis."""
    
    @staticmethod
    def calculate_trend(records):
        """
        Calculate trend using simple linear regression.
        Returns slope (positive = improving, negative = declining).
        """
        if len(records) < 2:
            return 0
        
        moods = [r.mood_score for r in records]
        x = list(range(len(moods)))
        
        mean_x = statistics.mean(x)
        mean_y = statistics.mean(moods)
        
        numerator = sum((x[i] - mean_x) * (moods[i] - mean_y) for i in range(len(x)))
        denominator = sum((xi - mean_x) ** 2 for xi in x)
        
        if denominator == 0:
            return 0
        
        slope = numerator / denominator
        return round(slope, 3)
    
    @staticmethod
    def identify_at_risk_users(days=30):
        """Identify users with declining trends."""
        # ✅ CORRIGÉ: wellbeing_records au lieu de wellbeingrecord
        start_date = timezone.now().date() - timedelta(days=days)
        users = User.objects.filter(wellbeing_records__isnull=False).distinct()
        
        at_risk = []
        
        for user in users:
            records = WellbeingRecord.objects.filter(
                user=user,
                date__gte=start_date
            ).order_by('date')
            
            if records.count() < 3:
                continue
            
            trend = PredictiveTrends.calculate_trend(records)
            latest_mood = records.last().mood_score
            
            # At risk if declining trend AND low current mood
            if trend < -0.1 and latest_mood < 6:
                at_risk.append({
                    'user': user,
                    'username': user.username,
                    'trend': trend,
                    'latest_mood': latest_mood,
                    'risk_level': 'high' if trend < -0.3 else 'medium',
                })
        
        return sorted(at_risk, key=lambda x: x['trend'])


class HeatmapData:
    """Generate heatmap data for temporal patterns."""
    
    @staticmethod
    def generate_hourly_heatmap(days=30):
        """
        Generate heatmap data by hour of day.
        Shows when users are most stressed/happy.
        """
        start_date = timezone.now().date() - timedelta(days=days)
        records = WellbeingRecord.objects.filter(date__gte=start_date)
        
        # Initialize heatmap (7 days x 24 hours)
        heatmap = {}
        for day in range(7):
            heatmap[day] = {}
            for hour in range(24):
                heatmap[day][hour] = {'mood': 0, 'count': 0}
        
        # Aggregate data
        for record in records:
            day_of_week = record.date.weekday()
            # Assume records are created at a consistent time (e.g., evening)
            hour = 20  # Default to 8 PM
            
            if day_of_week in heatmap and hour in heatmap[day_of_week]:
                heatmap[day_of_week][hour]['mood'] += record.mood_score
                heatmap[day_of_week][hour]['count'] += 1
        
        # Calculate averages
        for day in heatmap:
            for hour in heatmap[day]:
                if heatmap[day][hour]['count'] > 0:
                    heatmap[day][hour]['mood'] = round(
                        heatmap[day][hour]['mood'] / heatmap[day][hour]['count'], 1
                    )
        
        return heatmap
    
    @staticmethod
    def generate_daily_heatmap(days=30):
        """Generate heatmap data by day of week."""
        start_date = timezone.now().date() - timedelta(days=days)
        records = WellbeingRecord.objects.filter(date__gte=start_date)
        
        days_of_week = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        heatmap = {i: {'mood': 0, 'count': 0} for i in range(7)}
        
        for record in records:
            day_of_week = record.date.weekday()
            heatmap[day_of_week]['mood'] += record.mood_score
            heatmap[day_of_week]['count'] += 1
        
        # Calculate averages and format
        result = []
        for day_idx, day_name in enumerate(days_of_week):
            if heatmap[day_idx]['count'] > 0:
                avg_mood = round(heatmap[day_idx]['mood'] / heatmap[day_idx]['count'], 1)
            else:
                avg_mood = 0
            
            result.append({
                'day': day_name,
                'mood': avg_mood,
                'count': heatmap[day_idx]['count'],
            })
        
        return result
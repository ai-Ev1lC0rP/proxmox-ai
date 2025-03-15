"""
News source comparison and bias detection module for Mervin Follow.

This module provides functions to analyze news articles from different sources,
compare their coverage, and detect potential bias in reporting.
"""

import re
import nltk
import numpy as np
from collections import Counter, defaultdict
from typing import List, Dict, Any, Tuple, Optional
import os

# Try to download necessary NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('wordnet', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
except:
    print("Warning: Could not download NLTK data. Some analyzer features may not work.")

try:
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    from nltk.tokenize import word_tokenize, sent_tokenize
    from nltk.corpus import stopwords
    STOPWORDS = set(stopwords.words('english'))
except:
    print("Warning: Could not import all NLTK modules. Using simple fallbacks.")
    # Simple fallback
    STOPWORDS = {'the', 'and', 'a', 'to', 'of', 'in', 'is', 'it', 'that', 'for', 'on', 'with', 'as', 'was', 'be'}
    
    def word_tokenize(text):
        """Simple word tokenizer fallback"""
        return re.findall(r'\b\w+\b', text.lower())
    
    def sent_tokenize(text):
        """Simple sentence tokenizer fallback"""
        return re.split(r'[.!?]+', text)

# Bias-related words and phrases
BIAS_INDICATORS = {
    'conservative_bias': [
        'radical left', 'far left', 'socialist', 'leftist agenda', 'liberal elite',
        'mainstream media', 'fake news', 'Trump-hating', 'big government',
        'globalist', 'coastal elite', 'politically correct', 'cancel culture',
        'anti-American', 'patriot', 'freedom', 'liberty', 'constitutional',
        'traditional values', 'pro-life', 'activist judge', 'illegal immigrant',
        'strong borders', 'law and order', 'radical', 'woke', 'critical race theory',
        'indoctrination', 'radical gender ideology', 'tax burden'
    ],
    'liberal_bias': [
        'radical right', 'far right', 'alt-right', 'right-wing', 'extremist',
        'conspiracy theory', 'anti-science', 'climate denier', 'Trump supporter',
        'racist', 'sexist', 'homophobic', 'white privilege', 'patriarchy',
        'progressive', 'inclusive', 'diverse', 'systemic racism', 'marginalized', 
        'equality', 'reproductive rights', 'undocumented immigrant', 'humane immigration',
        'gun control', 'common sense reform', 'environmental justice', 'corporate greed',
        'disinformation', 'BIPOC', 'transphobic', 'hate speech'
    ]
}

# Highly loaded emotional words that might indicate bias
EMOTIONAL_WORDS = {
    'negative': [
        'terrible', 'horrible', 'awful', 'devastating', 'catastrophic',
        'disastrous', 'appalling', 'outrageous', 'disgraceful', 'shameful',
        'shocking', 'alarming', 'disturbing', 'horrific', 'tragic',
        'failed', 'dangerous', 'threat', 'crisis', 'chaotic',
        'disaster', 'catastrophe', 'nightmare', 'travesty', 'fiasco'
    ],
    'positive': [
        'excellent', 'wonderful', 'fantastic', 'amazing', 'outstanding',
        'remarkable', 'phenomenal', 'extraordinary', 'brilliant', 'superb',
        'triumph', 'victory', 'success', 'achievement', 'breakthrough',
        'historic', 'revolutionary', 'groundbreaking', 'innovative', 'visionary',
        'inspiring', 'impressive', 'exceptional', 'great', 'perfect'
    ]
}

def get_source_bias_rating(source_name: str) -> Dict[str, Any]:
    """
    Get the known bias rating of a news source, if available.
    Returns a dictionary with bias information.
    
    Sources are rated on a scale from -10 (extremely liberal) to +10 (extremely conservative),
    with 0 representing neutral/balanced.
    
    Reliability is rated from 0 (very unreliable) to 10 (highly reliable).
    """
    # Default rating
    default_rating = {
        'bias_score': 0,  # Neutral
        'bias_category': 'Unknown',
        'reliability': 5,  # Medium reliability
        'confidence': 'low'  # Low confidence in this rating
    }
    
    # Known bias ratings for common news sources
    # These ratings are approximations based on multiple media bias charts and studies
    bias_ratings = {
        'Associated Press': {'bias_score': 0, 'bias_category': 'Center', 'reliability': 9, 'confidence': 'high'},
        'Reuters': {'bias_score': 0, 'bias_category': 'Center', 'reliability': 9, 'confidence': 'high'},
        'BBC': {'bias_score': -1, 'bias_category': 'Center-Left', 'reliability': 8, 'confidence': 'high'},
        'Bloomberg': {'bias_score': -1, 'bias_category': 'Center-Left', 'reliability': 8, 'confidence': 'high'},
        'CNN': {'bias_score': -4, 'bias_category': 'Left', 'reliability': 6, 'confidence': 'high'},
        'MSNBC': {'bias_score': -7, 'bias_category': 'Far Left', 'reliability': 5, 'confidence': 'high'},
        'Fox News': {'bias_score': 7, 'bias_category': 'Far Right', 'reliability': 4, 'confidence': 'high'},
        'The Guardian': {'bias_score': -4, 'bias_category': 'Left', 'reliability': 7, 'confidence': 'high'},
        'New York Times': {'bias_score': -3, 'bias_category': 'Left', 'reliability': 8, 'confidence': 'high'},
        'Wall Street Journal': {'bias_score': 2, 'bias_category': 'Center-Right', 'reliability': 8, 'confidence': 'high'},
        'The Washington Post': {'bias_score': -3, 'bias_category': 'Left', 'reliability': 7, 'confidence': 'high'},
        'NPR': {'bias_score': -2, 'bias_category': 'Center-Left', 'reliability': 8, 'confidence': 'high'},
        'Breitbart': {'bias_score': 9, 'bias_category': 'Far Right', 'reliability': 2, 'confidence': 'high'},
        'HuffPost': {'bias_score': -6, 'bias_category': 'Far Left', 'reliability': 4, 'confidence': 'high'},
        'Daily Mail': {'bias_score': 5, 'bias_category': 'Right', 'reliability': 3, 'confidence': 'high'},
        'The Economist': {'bias_score': -1, 'bias_category': 'Center-Left', 'reliability': 9, 'confidence': 'high'},
        'Al Jazeera': {'bias_score': -2, 'bias_category': 'Center-Left', 'reliability': 7, 'confidence': 'high'},
        'Google News': {'bias_score': 0, 'bias_category': 'Center', 'reliability': 7, 'confidence': 'medium'},
        'News API': {'bias_score': 0, 'bias_category': 'Center', 'reliability': 6, 'confidence': 'low'},
    }
    
    # Normalize source name
    source_name = source_name.strip()
    
    # Return known rating or default
    return bias_ratings.get(source_name, default_rating)

def extract_keywords(text: str, top_n: int = 10) -> List[str]:
    """
    Extract the most important keywords from text.
    
    Args:
        text (str): The text to analyze
        top_n (int): Number of top keywords to return
        
    Returns:
        List[str]: List of top keywords
    """
    # Tokenize and clean the text
    try:
        words = word_tokenize(text.lower())
        words = [w for w in words if w.isalpha() and w not in STOPWORDS and len(w) > 2]
        
        # Count frequencies
        word_freq = Counter(words)
        
        # Get top keywords
        top_keywords = [word for word, _ in word_freq.most_common(top_n)]
        return top_keywords
    except Exception as e:
        print(f"Error extracting keywords: {e}")
        return []

def analyze_sentiment(text: str) -> Dict[str, float]:
    """
    Analyze the sentiment of a text.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        Dict[str, float]: Dictionary with sentiment scores
    """
    try:
        sid = SentimentIntensityAnalyzer()
        sentiment_scores = sid.polarity_scores(text)
        return sentiment_scores
    except Exception as e:
        print(f"Error analyzing sentiment: {e}")
        # Fallback to simpler approach
        positive_words = sum(1 for word in EMOTIONAL_WORDS['positive'] if word in text.lower())
        negative_words = sum(1 for word in EMOTIONAL_WORDS['negative'] if word in text.lower())
        
        # Calculate simple sentiment
        total = positive_words + negative_words
        if total == 0:
            return {'compound': 0, 'neg': 0, 'neu': 1, 'pos': 0}
        
        pos = positive_words / (total * 2)
        neg = negative_words / (total * 2)
        neu = 1 - (pos + neg)
        compound = (positive_words - negative_words) / total
        
        return {'compound': compound, 'neg': neg, 'neu': neu, 'pos': pos}

def detect_bias_language(text: str) -> Dict[str, Any]:
    """
    Detect potentially biased language in text.
    
    Args:
        text (str): The text to analyze
        
    Returns:
        Dict[str, Any]: Information about detected bias
    """
    text_lower = text.lower()
    
    # Check for bias indicators
    conservative_bias = []
    for phrase in BIAS_INDICATORS['conservative_bias']:
        if phrase.lower() in text_lower:
            conservative_bias.append(phrase)
    
    liberal_bias = []
    for phrase in BIAS_INDICATORS['liberal_bias']:
        if phrase.lower() in text_lower:
            liberal_bias.append(phrase)
    
    # Check for emotional language
    emotional_words = {
        'negative': [word for word in EMOTIONAL_WORDS['negative'] if word.lower() in text_lower],
        'positive': [word for word in EMOTIONAL_WORDS['positive'] if word.lower() in text_lower]
    }
    
    # Calculate bias metrics
    has_conservative_bias = len(conservative_bias) > 0
    has_liberal_bias = len(liberal_bias) > 0
    
    # If both sides are represented, we consider it more balanced
    if has_conservative_bias and has_liberal_bias:
        if len(conservative_bias) > len(liberal_bias) * 2:
            bias_direction = "conservative"
            bias_strength = min(10, len(conservative_bias) - len(liberal_bias))
        elif len(liberal_bias) > len(conservative_bias) * 2:
            bias_direction = "liberal"
            bias_strength = min(10, len(liberal_bias) - len(conservative_bias))
        else:
            bias_direction = "balanced"
            bias_strength = 0
    elif has_conservative_bias:
        bias_direction = "conservative"
        bias_strength = min(10, len(conservative_bias))
    elif has_liberal_bias:
        bias_direction = "liberal" 
        bias_strength = min(10, len(liberal_bias))
    else:
        bias_direction = "neutral"
        bias_strength = 0
    
    # Calculate emotional language metrics
    emotional_score = len(emotional_words['positive']) + len(emotional_words['negative'])
    emotional_balance = (len(emotional_words['positive']) - len(emotional_words['negative'])) / max(1, emotional_score)
    
    return {
        'bias_direction': bias_direction,
        'bias_strength': bias_strength,
        'conservative_bias_words': conservative_bias,
        'liberal_bias_words': liberal_bias,
        'emotional_language': {
            'score': emotional_score,
            'balance': emotional_balance,
            'positive': emotional_words['positive'],
            'negative': emotional_words['negative']
        }
    }

def analyze_article(article: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze a single article for various metrics.
    
    Args:
        article (Dict[str, Any]): The article to analyze
        
    Returns:
        Dict[str, Any]: Analysis results
    """
    # Extract the content
    content = article.get('content', '')
    title = article.get('title', '')
    source = article.get('source', 'Unknown')
    
    # Skip if no content
    if not content:
        return {
            'source': source,
            'error': 'No content to analyze'
        }
    
    # Get source bias information
    source_bias = get_source_bias_rating(source)
    
    # Extract keywords
    keywords = extract_keywords(content)
    
    # Analyze sentiment
    sentiment = analyze_sentiment(content)
    title_sentiment = analyze_sentiment(title)
    
    # Detect bias language
    bias_analysis = detect_bias_language(content)
    
    # Combine results
    return {
        'source': source,
        'title': title,
        'url': article.get('url', ''),
        'keywords': keywords,
        'content_length': len(content),
        'sentence_count': len(sent_tokenize(content)),
        'source_bias': source_bias,
        'content_sentiment': sentiment,
        'title_sentiment': title_sentiment,
        'bias_analysis': bias_analysis
    }

def compare_news_sources(articles: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Compare news articles from different sources about the same topic.
    
    Args:
        articles (List[Dict[str, Any]]): List of news articles
        
    Returns:
        Dict[str, Any]: Comparison results
    """
    if not articles:
        return {'error': 'No articles to compare'}
    
    # Group articles by source
    sources = defaultdict(list)
    for article in articles:
        sources[article.get('source', 'Unknown')].append(article)
    
    # Analyze each article
    analyzed_articles = []
    for article in articles:
        analysis = analyze_article(article)
        analyzed_articles.append(analysis)
    
    # Analyze differences between sources
    source_analyses = {}
    for source, articles_list in sources.items():
        # Skip if no articles
        if not articles_list:
            continue
        
        # Get analyses for this source
        source_analyses_list = [a for a in analyzed_articles if a['source'] == source]
        
        # Calculate aggregate metrics
        avg_sentiment = np.mean([a['content_sentiment']['compound'] for a in source_analyses_list])
        avg_bias_strength = np.mean([a['bias_analysis']['bias_strength'] for a in source_analyses_list])
        
        # Determine dominant bias direction
        bias_directions = [a['bias_analysis']['bias_direction'] for a in source_analyses_list]
        bias_direction_counts = Counter(bias_directions)
        dominant_bias = bias_direction_counts.most_common(1)[0][0] if bias_direction_counts else 'neutral'
        
        # Aggregate all bias words
        conservative_bias_words = set()
        liberal_bias_words = set()
        for a in source_analyses_list:
            conservative_bias_words.update(a['bias_analysis']['conservative_bias_words'])
            liberal_bias_words.update(a['bias_analysis']['liberal_bias_words'])
        
        # Aggregate keywords
        all_keywords = []
        for a in source_analyses_list:
            all_keywords.extend(a['keywords'])
        
        keywords_freq = Counter(all_keywords)
        top_keywords = [k for k, _ in keywords_freq.most_common(10)]
        
        # Store source analysis
        source_analyses[source] = {
            'article_count': len(articles_list),
            'avg_sentiment': avg_sentiment,
            'avg_bias_strength': avg_bias_strength,
            'dominant_bias': dominant_bias,
            'conservative_bias_words': list(conservative_bias_words),
            'liberal_bias_words': list(liberal_bias_words),
            'top_keywords': top_keywords,
            'source_bias_rating': get_source_bias_rating(source)
        }
    
    # Cross-source comparisons
    # Find common and unique keywords across sources
    all_source_keywords = {}
    for source, analysis in source_analyses.items():
        all_source_keywords[source] = set(analysis['top_keywords'])
    
    common_keywords = set.intersection(*all_source_keywords.values()) if all_source_keywords else set()
    unique_keywords = {
        source: kw - common_keywords for source, kw in all_source_keywords.items()
    }
    
    # Calculate bias and sentiment ranges
    all_sentiments = [analysis['avg_sentiment'] for analysis in source_analyses.values()]
    sentiment_range = max(all_sentiments) - min(all_sentiments) if all_sentiments else 0
    
    all_bias_strengths = [analysis['avg_bias_strength'] for analysis in source_analyses.values()]
    bias_strength_range = max(all_bias_strengths) - min(all_bias_strengths) if all_bias_strengths else 0
    
    # Generate comparison summary
    most_positive_source = max(source_analyses.items(), key=lambda x: x[1]['avg_sentiment'])[0] if source_analyses else None
    most_negative_source = min(source_analyses.items(), key=lambda x: x[1]['avg_sentiment'])[0] if source_analyses else None
    
    strongest_bias_source = max(source_analyses.items(), key=lambda x: x[1]['avg_bias_strength'])[0] if source_analyses else None
    
    # Return comprehensive comparison
    return {
        'individual_articles': analyzed_articles,
        'source_analyses': source_analyses,
        'common_keywords': list(common_keywords),
        'unique_keywords': {source: list(kws) for source, kws in unique_keywords.items()},
        'sentiment_range': sentiment_range,
        'bias_strength_range': bias_strength_range,
        'most_positive_source': most_positive_source,
        'most_negative_source': most_negative_source,
        'strongest_bias_source': strongest_bias_source,
        'sources_compared': list(sources.keys())
    }

def generate_comparison_report(comparison_results: Dict[str, Any], topic: str) -> str:
    """
    Generate a human-readable report from comparison results.
    
    Args:
        comparison_results (Dict[str, Any]): Results from compare_news_sources
        topic (str): The topic of the news articles
        
    Returns:
        str: A formatted report
    """
    if 'error' in comparison_results:
        return f"Error generating comparison: {comparison_results['error']}"
    
    # Start building the report
    report = f"# News Source Comparison Report: {topic}\n\n"
    
    # Sources overview
    sources = comparison_results['sources_compared']
    report += f"## Sources Compared ({len(sources)} total)\n\n"
    
    for source in sources:
        source_analysis = comparison_results['source_analyses'].get(source, {})
        source_bias = source_analysis.get('source_bias_rating', {})
        bias_category = source_bias.get('bias_category', 'Unknown')
        reliability = source_bias.get('reliability', 0)
        
        # Format reliability as stars
        reliability_stars = '★' * reliability + '☆' * (10 - reliability)
        
        report += f"- **{source}** ({bias_category}) - Reliability: {reliability_stars}\n"
    
    report += "\n## Key Findings\n\n"
    
    # Coverage differences
    report += "### Common Topics Across Sources\n\n"
    common_keywords = comparison_results.get('common_keywords', [])
    if common_keywords:
        report += "All sources discussed: " + ", ".join(common_keywords) + "\n\n"
    else:
        report += "No common topics found across all sources.\n\n"
    
    # Unique perspectives
    report += "### Unique Source Perspectives\n\n"
    unique_keywords = comparison_results.get('unique_keywords', {})
    for source, keywords in unique_keywords.items():
        if keywords:
            report += f"**{source}** uniquely emphasized: " + ", ".join(keywords) + "\n\n"
    
    # Sentiment analysis
    report += "### Tone and Sentiment\n\n"
    most_positive = comparison_results.get('most_positive_source')
    most_negative = comparison_results.get('most_negative_source')
    
    if most_positive:
        report += f"- **{most_positive}** had the most positive coverage\n"
    if most_negative:
        report += f"- **{most_negative}** had the most negative coverage\n"
    
    sentiment_range = comparison_results.get('sentiment_range', 0)
    if sentiment_range > 0.4:
        report += f"- **Notable sentiment disparity** detected (range: {sentiment_range:.2f})\n"
    else:
        report += f"- Similar emotional tone across sources (sentiment range: {sentiment_range:.2f})\n"
    
    report += "\n### Bias Analysis\n\n"
    strongest_bias = comparison_results.get('strongest_bias_source')
    if strongest_bias:
        source_analysis = comparison_results['source_analyses'].get(strongest_bias, {})
        bias_dir = source_analysis.get('dominant_bias', 'neutral')
        bias_str = source_analysis.get('avg_bias_strength', 0)
        
        if bias_str > 3:
            report += f"- **{strongest_bias}** showed the strongest {bias_dir} bias in their reporting\n"
    
    # Detailed source analysis
    report += "\n## Detailed Source Analysis\n\n"
    
    for source in sources:
        source_analysis = comparison_results['source_analyses'].get(source, {})
        if not source_analysis:
            continue
            
        report += f"### {source}\n\n"
        
        # Add bias information
        bias_dir = source_analysis.get('dominant_bias', 'neutral')
        bias_str = source_analysis.get('avg_bias_strength', 0)
        
        if bias_str > 0:
            report += f"- **Bias detected**: {bias_dir.capitalize()} (strength: {bias_str:.1f}/10)\n"
        else:
            report += "- **Bias analysis**: Neutral coverage\n"
        
        # Add sentiment
        sentiment = source_analysis.get('avg_sentiment', 0)
        if sentiment > 0.25:
            sentiment_desc = "Very positive"
        elif sentiment > 0.1:
            sentiment_desc = "Somewhat positive"
        elif sentiment < -0.25:
            sentiment_desc = "Very negative"
        elif sentiment < -0.1:
            sentiment_desc = "Somewhat negative"
        else:
            sentiment_desc = "Neutral"
            
        report += f"- **Tone**: {sentiment_desc} (sentiment score: {sentiment:.2f})\n"
        
        # Key terms
        top_keywords = source_analysis.get('top_keywords', [])
        if top_keywords:
            report += f"- **Key terms**: {', '.join(top_keywords)}\n"
        
        # Bias indicators
        conservative_words = source_analysis.get('conservative_bias_words', [])
        liberal_words = source_analysis.get('liberal_bias_words', [])
        
        if conservative_words:
            report += f"- **Conservative-leaning language**: {', '.join(conservative_words[:5])}"
            if len(conservative_words) > 5:
                report += f" and {len(conservative_words) - 5} more"
            report += "\n"
            
        if liberal_words:
            report += f"- **Liberal-leaning language**: {', '.join(liberal_words[:5])}"
            if len(liberal_words) > 5:
                report += f" and {len(liberal_words) - 5} more"
            report += "\n"
            
        report += "\n"
    
    report += "## Conclusion\n\n"
    
    # Generate conclusion based on findings
    bias_strength_range = comparison_results.get('bias_strength_range', 0)
    
    if bias_strength_range > 5:
        report += "There are **significant differences** in how sources covered this topic. "
        report += "Consider reading multiple sources to get a balanced perspective.\n\n"
    elif bias_strength_range > 2:
        report += "There are **moderate differences** in how sources covered this topic. "
        report += "Some sources may emphasize different aspects or use different framing.\n\n"
    else:
        report += "There is **relatively consistent coverage** across sources for this topic. "
        report += "Most sources presented similar information with minimal bias differences.\n\n"
    
    return report

def analyze_and_compare_news(articles: List[Dict[str, Any]], topic: str) -> str:
    """
    Main function to analyze and compare news from different sources.
    
    Args:
        articles (List[Dict[str, Any]]): List of news articles
        topic (str): The topic of the news articles
        
    Returns:
        str: A formatted report comparing the sources
    """
    if not articles:
        return "No articles provided for comparison."
    
    # Check if we have enough sources to compare
    sources = set(article.get('source', 'Unknown') for article in articles)
    if len(sources) < 2:
        return f"Comparison requires at least two different news sources. Only found: {', '.join(sources)}"
    
    try:
        # Perform comparison analysis
        comparison_results = compare_news_sources(articles)
        
        # Generate human-readable report
        report = generate_comparison_report(comparison_results, topic)
        
        return report
    except Exception as e:
        return f"Error performing news comparison: {str(e)}"

if __name__ == "__main__":
    # Test with sample data
    sample_articles = [
        {
            'title': 'Economy shows signs of growth despite challenges',
            'content': 'The economy has shown remarkable resilience in the face of global challenges. Experts suggest the growth is sustainable.',
            'source': 'Reuters',
            'url': 'https://example.com/reuters/economy'
        },
        {
            'title': 'Economic disaster looms as inflation soars',
            'content': 'The radical left policies have led to catastrophic inflation and an economy on the brink of collapse.',
            'source': 'Fox News',
            'url': 'https://example.com/foxnews/economy'
        },
        {
            'title': 'Economy rebounds as progressive policies take effect',
            'content': 'New data shows the economy is recovering thanks to progressive economic policies, despite right-wing obstruction.',
            'source': 'MSNBC',
            'url': 'https://example.com/msnbc/economy'
        }
    ]
    
    report = analyze_and_compare_news(sample_articles, "Economy")
    print(report)

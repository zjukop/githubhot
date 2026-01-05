import sys
from loguru import logger
from src.crawler import crawl_trending
from src.article_generator import ArticleGenerator

def main():
    logger.info("Step 1: Fetching trending repos to pick a candidate...")
    result = crawl_trending()
    
    if not result.repos:
        logger.error("No repositories found!")
        sys.exit(1)

    # Strategy: Pick the repo with the highest stars_today, or just the first one.
    # Trending list is usually sorted, but let's be sure we pick a "hot" one.
    # Filter out repos with no description or very short readme if possible? 
    # For now, just pick the #1 trending repo.
    target_repo = result.repos[0]
    
    logger.info(f"Selected candidate: {target_repo.name} (+{target_repo.stars_today} stars today)")
    logger.info(f"URL: {target_repo.url}")

    # Generate Article
    logger.info("Step 2: Generating WeChat Official Account Article...")
    generator = ArticleGenerator()
    try:
        content = generator.generate_article(target_repo)
        filename = generator.save_article(target_repo, content)
        
        print("\n" + "="*50)
        print(f"✅ Article generated successfully: {filename}")
        print("="*50 + "\n")
        
        # Preview first few lines
        print("\n".join(content.splitlines()[:10]))
        
    except Exception as e:
        logger.error(f"Failed to generate article: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

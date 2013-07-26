import pstats



stats = pstats.Stats(r'profile.stats')

stats.sort_stats('calls')


stats.print_stats()
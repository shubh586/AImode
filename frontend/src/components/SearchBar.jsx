import { Search, Sparkles, ArrowRight } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';

const SUGGESTIONS = [
  "How does quantum computing work?",
  "What are the latest advances in AI?",
  "Explain blockchain technology",
  "How does CRISPR gene editing work?",
  "What causes climate change?",
  "How do neural networks learn?",
];

export default function SearchBar({ onSearch, isLoading }) {
  const handleSubmit = (e) => {
    e.preventDefault();
    const query = new FormData(e.target).get('query')?.trim();
    if (query) onSearch(query);
  };

  return (
    <div className="w-full max-w-2xl mx-auto">
      {/* Brand */}
      <div className="text-center mb-10 animate-fade-in-up">
        <div className="inline-flex items-center gap-3 mb-4">
          <div className="w-11 h-11 rounded-xl bg-gradient-to-br from-[var(--accent-indigo)] to-[var(--accent-violet)] flex items-center justify-center shadow-lg">
            <Sparkles className="w-5 h-5 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-foreground">AI Mode</h1>
        </div>
        <p className="text-muted-foreground text-base">
          Research-grade answers powered by intelligent AI agents
        </p>
      </div>

      {/* Search */}
      <form onSubmit={handleSubmit} className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
        <div className="relative">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-muted-foreground" />
          <Input
            type="text"
            name="query"
            className="w-full pl-12 pr-14 py-6 text-base bg-card border-border rounded-xl focus-visible:ring-1 focus-visible:ring-primary"
            placeholder="Ask anything..."
            disabled={isLoading}
            autoFocus
            autoComplete="off"
            id="search-input"
          />
          <Button
            type="submit"
            size="icon"
            disabled={isLoading}
            id="search-button"
            aria-label="Search"
            className="absolute right-2 top-1/2 -translate-y-1/2 bg-gradient-to-br from-[var(--accent-indigo)] to-[var(--accent-violet)] hover:opacity-90 rounded-lg h-9 w-9"
          >
            <ArrowRight className="w-4 h-4" />
          </Button>
        </div>
      </form>

      {/* Suggestions */}
      <div className="flex flex-wrap gap-2 justify-center mt-6 animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
        {SUGGESTIONS.map((s, i) => (
          <Badge
            key={i}
            variant="outline"
            className="cursor-pointer text-muted-foreground hover:text-foreground hover:bg-muted/50 px-3 py-1.5 text-sm rounded-full transition-colors"
            onClick={() => onSearch(s)}
            id={`suggestion-${i}`}
          >
            {s}
          </Badge>
        ))}
      </div>
    </div>
  );
}

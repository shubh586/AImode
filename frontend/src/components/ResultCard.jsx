import ReactMarkdown from 'react-markdown';
import { Sparkles, BookOpen } from 'lucide-react';
import SourceCard from './SourceCard';
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';

export default function ResultCard({ answer, citations = [] }) {
  return (
    <div className="w-full max-w-3xl mx-auto animate-fade-in-up">
      {/* Answer */}
      <Card className="mb-6 bg-card/80 border-border">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--accent-indigo)] to-[var(--accent-violet)] flex items-center justify-center">
              <Sparkles className="w-4 h-4 text-white" />
            </div>
            <div>
              <CardTitle className="text-base text-foreground">AI Answer</CardTitle>
              <p className="text-xs text-muted-foreground mt-0.5">
                From {citations.length} source{citations.length !== 1 ? 's' : ''}
              </p>
            </div>
          </div>
        </CardHeader>
        <Separator className="mx-6 w-auto" />
        <CardContent className="pt-5">
          <div className="answer-content" id="answer-content">
            <ReactMarkdown>{answer}</ReactMarkdown>
          </div>
        </CardContent>
      </Card>

      {/* Sources */}
      {citations.length > 0 && (
        <div className="mb-8 animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
          <div className="flex items-center gap-2 mb-3 px-1">
            <BookOpen className="w-4 h-4 text-muted-foreground" />
            <h3 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Sources</h3>
            <Badge variant="secondary" className="text-xs px-1.5 py-0">{citations.length}</Badge>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 stagger-children">
            {citations.map((source, index) => (
              <SourceCard key={index} source={source} index={index} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

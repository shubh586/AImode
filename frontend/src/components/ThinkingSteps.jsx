import {
  PenLine, Map, Globe, Filter, FileText, Brain, Quote,
  CheckCircle2, Loader2, Circle,
} from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';

const STEPS_CONFIG = [
  { key: 'query_rewriter', label: 'Rewriting Query', icon: PenLine },
  { key: 'search_planner', label: 'Planning Search', icon: Map },
  { key: 'web_search', label: 'Searching the Web', icon: Globe },
  { key: 'document_filter', label: 'Filtering Results', icon: Filter },
  { key: 'source_summaries', label: 'Summarizing Sources', icon: FileText },
  { key: 'answer_generator', label: 'Generating Answer', icon: Brain },
  { key: 'add_citations', label: 'Adding Citations', icon: Quote },
];

export default function ThinkingSteps({ stepsCompleted = [], currentStep, stepData = {} }) {
  return (
    <div className="w-full max-w-3xl mx-auto mb-4">
      <Card className="bg-card/80 border-border">
        <CardContent className="p-4">
          <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-3 flex items-center gap-2">
            <span className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
            Research Pipeline
          </p>

          <div className="space-y-0.5">
            {STEPS_CONFIG.map((step) => {
              const isCompleted = stepsCompleted.includes(step.key);
              const isActive = currentStep === step.key && !isCompleted;
              const Icon = step.icon;

              return (
                <div
                  key={step.key}
                  className={`flex items-center gap-2.5 px-3 py-2 rounded-md text-sm transition-colors ${
                    isCompleted
                      ? 'text-[var(--accent-emerald)] bg-[var(--accent-emerald)]/5'
                      : isActive
                      ? 'text-[var(--accent-cyan)] bg-[var(--accent-cyan)]/5'
                      : 'text-muted-foreground/50'
                  }`}
                >
                  {/* Status */}
                  {isCompleted ? (
                    <CheckCircle2 className="w-4 h-4 flex-shrink-0" />
                  ) : isActive ? (
                    <Loader2 className="w-4 h-4 flex-shrink-0 animate-spin" />
                  ) : (
                    <Circle className="w-4 h-4 flex-shrink-0 opacity-40" />
                  )}

                  <Icon className="w-4 h-4 flex-shrink-0" />
                  <span className="flex-1 font-medium">{step.label}</span>

                  {/* Extra data */}
                  {isCompleted && step.key === 'web_search' && stepData.documents_found !== undefined && (
                    <span className="text-xs text-muted-foreground">{stepData.documents_found} found</span>
                  )}
                  {isCompleted && step.key === 'document_filter' && stepData.filtered_count !== undefined && (
                    <span className="text-xs text-muted-foreground">{stepData.filtered_count} relevant</span>
                  )}
                  {isCompleted && step.key === 'query_rewriter' && stepData.rewritten_query && (
                    <span className="text-xs text-muted-foreground truncate max-w-[200px]" title={stepData.rewritten_query}>
                      "{stepData.rewritten_query}"
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

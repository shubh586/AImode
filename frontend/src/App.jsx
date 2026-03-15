import { useState, useRef } from 'react';
import { Search, ArrowLeft, RotateCcw, ChevronDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Separator } from '@/components/ui/separator';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import SearchBar from './components/SearchBar';
import ThinkingSteps from './components/ThinkingSteps';
import LoadingAnimation from './components/LoadingAnimation';
import ResultCard from './components/ResultCard';

export default function App() {
  const [view, setView] = useState('home');       // home | loading | result | error
  const [query, setQuery] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [stepsCompleted, setStepsCompleted] = useState([]);
  const [currentStep, setCurrentStep] = useState('');
  const [stepData, setStepData] = useState({});
  const [answer, setAnswer] = useState('');
  const [citations, setCitations] = useState([]);
  const [error, setError] = useState('');
  const abortControllerRef = useRef(null);
  const [pipelineOpen, setPipelineOpen] = useState(false);

  // Kick off a search — streams results from the backend via SSE
  const handleSearch = async (searchQuery) => {
    setQuery(searchQuery);
    setView('loading');
    setIsLoading(true);
    setStepsCompleted([]);
    setCurrentStep('query_rewriter');
    setStepData({});
    setAnswer('');
    setCitations([]);
    setError('');

    // Cancel any in-flight request
    if (abortControllerRef.current) abortControllerRef.current.abort();
    const controller = new AbortController();
    abortControllerRef.current = controller;

    try {
      const response = await fetch('/api/search/stream', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery }),
        signal: controller.signal,
      });

      if (!response.ok) throw new Error(`Server error: ${response.status}`);

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';
      let hasError = false;

      // Read the SSE stream chunk by chunk
      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              if (data.step === 'error') hasError = true;
              processStreamEvent(data);
            } catch (e) { /* skip malformed JSON */ }
          }
        }
      }

      // Handle anything left in the buffer
      if (buffer.startsWith('data: ')) {
        try {
          const data = JSON.parse(buffer.slice(6));
          if (data.step === 'error') hasError = true;
          processStreamEvent(data);
        } catch (e) { /* skip */ }
      }

      if (!hasError) setView('result');
    } catch (err) {
      if (err.name === 'AbortError') return;
      setError(err.message || 'Something went wrong. Please try again.');
      setView('error');
    } finally {
      setIsLoading(false);
    }
  };

  // Handle each SSE event — update the step progress and capture results
  const processStreamEvent = (data) => {
    const step = data.step;
    if (step === 'error') { setError(data.error || 'Pipeline error'); setView('error'); return; }
    if (step === 'complete') { setCurrentStep(''); return; }
    if (data.steps_completed) setStepsCompleted(data.steps_completed);

    // Figure out which step comes next
    const STEP_ORDER = [
      'query_rewriter', 'search_planner', 'web_search',
      'document_filter', 'source_summaries', 'answer_generator', 'add_citations'
    ];
    const idx = STEP_ORDER.indexOf(step);
    setCurrentStep(idx < STEP_ORDER.length - 1 ? STEP_ORDER[idx + 1] : '');
    setStepData((prev) => ({ ...prev, ...data }));

    // Grab the answer / citations when they come through
    if (data.answer) setAnswer(data.answer);
    if (data.cited_answer) setAnswer(data.cited_answer);
    if (data.citations) setCitations(data.citations);
  };

  const handleBack = () => {
    if (abortControllerRef.current) abortControllerRef.current.abort();
    setView('home');
    setIsLoading(false);
    setStepsCompleted([]);
    setCurrentStep('');
  };

  const handleRetry = () => { if (query) handleSearch(query); };

  // Shared top bar for loading + result views
  const TopBar = ({ showRetry = false }) => (
    <div className="max-w-3xl mx-auto mb-6">
      <div className="flex items-center gap-3 py-2">
        <Button
          variant="ghost"
          size="icon"
          onClick={handleBack}
          className="text-muted-foreground hover:text-foreground"
          id="back-button"
          aria-label="Go back"
        >
          <ArrowLeft className="w-5 h-5" />
        </Button>
        <div className="flex-1 min-w-0">
          <p className="text-sm text-muted-foreground truncate flex items-center gap-2">
            <Search className="w-3.5 h-3.5 flex-shrink-0" />
            {query}
          </p>
        </div>
        {showRetry && (
          <Button
            variant="ghost"
            size="icon"
            onClick={handleRetry}
            className="text-muted-foreground hover:text-foreground"
            id="retry-button"
            aria-label="Retry search"
          >
            <RotateCcw className="w-4 h-4" />
          </Button>
        )}
      </div>
      <Separator />
    </div>
  );

  return (
    <div className="relative min-h-screen">
      <div className="gradient-mesh" />

      <div className="relative z-10">
        {/* Home — centered search bar */}
        {view === 'home' && (
          <div className="min-h-screen flex flex-col items-center justify-center px-4 pb-20">
            <SearchBar onSearch={handleSearch} isLoading={isLoading} />
          </div>
        )}

        {/* Loading — pipeline progress + spinner */}
        {view === 'loading' && (
          <div className="min-h-screen px-4 pt-6 pb-20">
            <TopBar />
            <ThinkingSteps stepsCompleted={stepsCompleted} currentStep={currentStep} stepData={stepData} />
            <LoadingAnimation />
          </div>
        )}

        {/* Result — answer card + sources */}
        {view === 'result' && (
          <div className="min-h-screen px-4 pt-6 pb-20">
            <TopBar showRetry />

            {/* Collapsible pipeline summary */}
            <div className="max-w-3xl mx-auto mb-6">
              <Collapsible open={pipelineOpen} onOpenChange={setPipelineOpen}>
                <CollapsibleTrigger asChild>
                  <button
                    className="flex items-center gap-2 w-full text-left px-3 py-2 rounded-lg text-sm text-muted-foreground hover:text-foreground hover:bg-muted/50 transition-colors"
                    id="pipeline-toggle"
                  >
                    <div className="w-2 h-2 rounded-full bg-[var(--accent-emerald)]" />
                    <span>Research complete — {stepsCompleted.length} steps</span>
                    <ChevronDown className={`w-4 h-4 ml-auto transition-transform ${pipelineOpen ? 'rotate-180' : ''}`} />
                  </button>
                </CollapsibleTrigger>
                <CollapsibleContent className="pt-2">
                  <ThinkingSteps stepsCompleted={stepsCompleted} currentStep="" stepData={stepData} />
                </CollapsibleContent>
              </Collapsible>
            </div>

            <ResultCard answer={answer} citations={citations} />

            {/* Follow-up question input */}
            <div className="max-w-3xl mx-auto mt-8 animate-fade-in" style={{ animationDelay: '0.4s' }}>
              <form onSubmit={(e) => {
                e.preventDefault();
                const q = new FormData(e.target).get('query')?.trim();
                if (q) handleSearch(q);
              }}>
                <div className="relative">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
                  <Input
                    type="text"
                    name="query"
                    className="pl-9 bg-card border-border"
                    placeholder="Ask a follow-up question..."
                    autoComplete="off"
                    id="followup-input"
                  />
                </div>
              </form>
            </div>
          </div>
        )}

        {/* Error fallback */}
        {view === 'error' && (
          <div className="min-h-screen flex flex-col items-center justify-center px-4 pb-20">
            <div className="text-center max-w-md animate-fade-in-up">
              <div className="w-14 h-14 rounded-full bg-destructive/10 flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">⚠️</span>
              </div>
              <h2 className="text-xl font-semibold text-foreground mb-2">Something went wrong</h2>
              <p className="text-sm text-muted-foreground mb-6">
                {error || 'An unexpected error occurred. Please try again.'}
              </p>
              <div className="flex gap-3 justify-center">
                <Button onClick={handleRetry} id="retry-error-button">Try Again</Button>
                <Button variant="outline" onClick={handleBack} id="home-error-button">Go Home</Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

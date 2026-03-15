import { Loader2 } from 'lucide-react';

export default function LoadingAnimation() {
  return (
    <div className="flex items-center justify-center py-10 gap-4">
      <Loader2 className="w-6 h-6 animate-spin text-primary" />
      <div>
        <p className="text-sm font-medium text-foreground">Researching your question</p>
        <p className="text-xs text-muted-foreground mt-0.5">AI agents are working on it…</p>
      </div>
    </div>
  );
}

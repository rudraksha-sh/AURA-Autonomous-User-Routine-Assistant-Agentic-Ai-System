import type { Goal } from "@/types/goal";
import { GoalCard } from "@/components/goals/GoalCard";

type GoalListProps = {
  goals: Goal[];
  isLoading: boolean;
  deletingGoalId: number | null;
  onDelete: (goalId: number) => Promise<void>;
};

export function GoalList({
  goals,
  isLoading,
  deletingGoalId,
  onDelete,
}: GoalListProps) {
  if (isLoading) {
    return (
      <div className="mt-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
        <p className="text-sm text-slate-500">
          Loading your goals...
        </p>
      </div>
    );
  }

  if (goals.length === 0) {
    return (
      <div className="mt-4 rounded-2xl border border-dashed border-slate-300 bg-white p-8 text-center">
        <p className="text-sm font-medium text-slate-700">
          No goals yet.
        </p>

        <p className="mt-1 text-sm text-slate-500">
          Create your first goal above.
        </p>
      </div>
    );
  }

  return (
    <div className="mt-4 grid gap-4">
      {goals.map((goal) => (
        <GoalCard
          key={goal.id}
          goal={goal}
          onDelete={onDelete}
          isDeleting={deletingGoalId === goal.id}
        />
      ))}
    </div>
  );
}
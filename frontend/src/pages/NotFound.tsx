import { Link } from "react-router-dom";

export function NotFound() {
  return (
    <div className="py-16 text-center">
      <h1 className="text-2xl font-bold text-slate-900">Page not found</h1>
      <p className="mt-2 text-sm text-slate-600">This route doesn't exist.</p>
      <Link to="/" className="mt-4 inline-block text-sm font-medium text-indigo-600 hover:underline">
        ← Back to dashboard
      </Link>
    </div>
  );
}

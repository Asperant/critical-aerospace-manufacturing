import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <section aria-labelledby="not-found-heading">
      <h1 id="not-found-heading">Page not found</h1>
      <p>
        <Link to="/overview">Go to the overview</Link>
      </p>
    </section>
  );
}

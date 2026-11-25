import React, { lazy, Suspense } from "react";
import Landing from "../landing/Landing";

const App = lazy(() => import("../App"));

export default function Entry() {
  const [dashboard, setDashboard] = React.useState(() =>
    location.hash.startsWith("#/dashboard"),
  );
  React.useEffect(() => {
    const update = () => {
      setDashboard(location.hash.startsWith("#/dashboard"));
      if (location.hash.startsWith("#/dashboard")) window.scrollTo(0, 0);
    };
    window.addEventListener("hashchange", update);
    return () => window.removeEventListener("hashchange", update);
  }, []);
  return dashboard ? (
    <Suspense
      fallback={
        <div role="status" style={{ padding: "2rem" }}>
          Opening workspace…
        </div>
      }
    >
      <App />
    </Suspense>
  ) : (
    <Landing />
  );
}

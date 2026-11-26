import React, { lazy, Suspense } from "react";
import Landing from "../landing/Landing";

const App = lazy(() => import("../App"));

function isDashboardRoute() {
  if (location.hash.startsWith("#/dashboard")) {
    const cleanPath = location.hash.slice(1);
    window.history.replaceState(null, "", cleanPath);
    return true;
  }
  return location.pathname.startsWith("/dashboard");
}

export default function Entry() {
  const [dashboard, setDashboard] = React.useState(isDashboardRoute);
  React.useEffect(() => {
    const update = () => {
      const next = isDashboardRoute();
      setDashboard(next);
      if (next) window.scrollTo(0, 0);
    };
    window.addEventListener("popstate", update);
    window.addEventListener("hashchange", update);
    return () => {
      window.removeEventListener("popstate", update);
      window.removeEventListener("hashchange", update);
    };
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

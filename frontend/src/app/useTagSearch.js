import { useEffect, useState } from "react";
import { request } from "../services/api";

export default function useTagSearch(query) {
  const [results, setResults] = useState(null);

  useEffect(() => {
    const match = /^tag:([A-Za-z][A-Za-z0-9_.-]{0,63})=(.{1,256})$/i.exec(
      query.trim(),
    );
    if (!match) {
      setResults(null);
      return;
    }
    let active = true;
    const timer = setTimeout(() => {
      request(
        `/runs/search?tag_key=${encodeURIComponent(match[1])}&tag_value=${encodeURIComponent(match[2])}`,
      )
        .then((value) => {
          if (active) setResults(value);
        })
        .catch(() => {
          if (active)
            setResults({
              tag: { key: match[1], value: match[2] },
              runs: [],
              experiments: [],
              models: [],
              error: "Tag search is unavailable.",
            });
        });
    }, 250);
    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [query]);

  return results;
}

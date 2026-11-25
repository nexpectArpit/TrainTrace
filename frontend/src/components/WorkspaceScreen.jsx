import React from "react";
import Investigations from "../screens/Investigations";
import Training from "../screens/Training";
import Compare from "../screens/Compare";
import Audits from "../screens/Audits";
import Decisions from "../screens/Decisions";
import History from "../screens/History";
import Registry from "../screens/Registry";
import Inference from "../screens/Inference";
import Search from "../screens/Search";
import WorkflowNavigation from "./WorkflowNavigation";

const screens = {
  Investigations,
  Training,
  Compare,
  Audits,
  Decisions,
  History,
  Registry,
  Inference,
  Search,
};

export default function WorkspaceScreen({ workspace }) {
  const Screen = screens[workspace.tab];
  return Screen ? (
    <>
      <Screen workspace={workspace} />
      <WorkflowNavigation workspace={workspace} />
    </>
  ) : null;
}

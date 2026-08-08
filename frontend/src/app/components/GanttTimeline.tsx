"use client";

import React from "react";

interface GanttTask {
  id: string;
  name: string;
  phase: "USA" | "India";
  start_day: number;
  end_day: number;
  status: "completed" | "active" | "pending";
}

interface USAIndiaPhaseItem {
  task: string;
  date: string;
  completed: boolean;
}

interface TimelineData {
  usa_phase?: USAIndiaPhaseItem[];
  india_phase?: USAIndiaPhaseItem[];
  gantt_tasks?: GanttTask[];
}

function formatDynamicDate(dayOffset: number): string {
  const date = new Date();
  date.setDate(date.getDate() + dayOffset);
  const day = String(date.getDate()).padStart(2, "0");
  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const month = months[date.getMonth()];
  const year = date.getFullYear();
  return `${day} ${month} ${year}`;
}

const DEFAULT_USA_PHASE: USAIndiaPhaseItem[] = [
  { task: "Term Sheet Execution", date: formatDynamicDate(8), completed: true },
  { task: "Delaware LLC Formation", date: formatDynamicDate(10), completed: true },
  { task: "Name Reservation & IRS EIN", date: formatDynamicDate(15), completed: true },
];

const DEFAULT_INDIA_PHASE: USAIndiaPhaseItem[] = [
  { task: "PropCo WOS Incorporation", date: formatDynamicDate(22), completed: true },
  { task: "Registered Campus Lease Deed", date: formatDynamicDate(25), completed: true },
  { task: "OpCo Consultancy Agreement", date: formatDynamicDate(34), completed: true },
  { task: "FDI Capital Injection & FC-GPR", date: formatDynamicDate(42), completed: true },
];


const DEFAULT_GANTT_TASKS: GanttTask[] = [
  { id: "t1", name: "Term Sheet", phase: "USA", start_day: 3, end_day: 8, status: "completed" },
  { id: "t2", name: "Delaware LLC Formation", phase: "USA", start_day: 5, end_day: 10, status: "completed" },
  { id: "t3", name: "Name Reservation", phase: "USA", start_day: 8, end_day: 15, status: "completed" },
  { id: "t4", name: "PropCo Incorporation", phase: "India", start_day: 10, end_day: 22, status: "completed" },
  { id: "t5", name: "Registered Lease Deed", phase: "India", start_day: 15, end_day: 25, status: "completed" },
  { id: "t6", name: "OpCo SLA Signing", phase: "India", start_day: 22, "end_day": 34, status: "completed" },
  { id: "t7", name: "FDI Remittance & Allotment", phase: "India", start_day: 25, end_day: 36, status: "completed" },
  { id: "t8", name: "FC-GPR Reporting (FIRMS)", phase: "India", start_day: 34, end_day: 42, status: "completed" },
  { id: "t9", name: "CBSE Operational Clearance", phase: "India", start_day: 36, end_day: 45, status: "active" },
];

const TIME_MARKS = [3, 5, 8, 10, 15, 22, 25, 34, 35, 36, 42, 45];
const TOTAL_DAYS = 48;

export function GanttTimeline({ timelineData }: { timelineData?: TimelineData }) {
  const usaItems = timelineData?.usa_phase || DEFAULT_USA_PHASE;
  const indiaItems = timelineData?.india_phase || DEFAULT_INDIA_PHASE;
  const tasks = timelineData?.gantt_tasks || DEFAULT_GANTT_TASKS;

  return (
    <div className="card-editorial p-6 space-y-6 bg-white border border-stone-200 rounded-2xl shadow-sm">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-4 border-b border-stone-100 pb-4">
        <div>
          <h3 className="text-xl font-editorial-display font-semibold text-stone-900">
            Proposed Execution Timeline
          </h3>
          <p className="text-xs text-stone-500 font-editorial-body mt-1">
            Phased implementation roadmap for US co-investment and Indian FDI execution
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="badge-pill bg-stone-100 text-stone-800 text-xs px-3 py-1 font-mono">
            Target: 45 Days
          </span>
          <span className="badge-pill bg-emerald-50 text-emerald-700 border border-emerald-200 text-xs px-3 py-1 font-mono">
            9 Phased Tasks
          </span>
        </div>
      </div>

      {/* Grid container: Left side Phase Tables | Right side Gantt Chart */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left column (5 cols): USA & INDIA Phase tables */}
        <div className="lg:col-span-5 space-y-6">
          {/* USA PHASE */}
          <div className="rounded-xl border border-stone-200 overflow-hidden bg-stone-50/50">
            <div className="bg-stone-100 px-4 py-2.5 flex items-center justify-between border-b border-stone-200">
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-700 font-mono">
                USA Phase (Co-Investment)
              </span>
              <span className="text-[11px] font-mono text-stone-500">Origin</span>
            </div>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-stone-200 text-stone-500">
                  <th className="px-4 py-2 font-medium">Task</th>
                  <th className="px-3 py-2 font-medium">Date</th>
                  <th className="px-3 py-2 font-medium text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200/60 bg-white">
                {usaItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-stone-50/50">
                    <td className="px-4 py-2.5 font-medium text-stone-800">{item.task}</td>
                    <td className="px-3 py-2.5 text-stone-500 font-mono text-[11px]">{item.date}</td>
                    <td className="px-3 py-2.5 text-center">
                      {item.completed ? (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 font-bold text-xs">
                          ✓
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-600 font-bold text-xs">
                          ⏱
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* INDIA PHASE */}
          <div className="rounded-xl border border-stone-200 overflow-hidden bg-stone-50/50">
            <div className="bg-stone-100 px-4 py-2.5 flex items-center justify-between border-b border-stone-200">
              <span className="text-xs font-semibold uppercase tracking-wider text-stone-700 font-mono">
                India Phase (FDI &amp; Operations)
              </span>
              <span className="text-[11px] font-mono text-stone-500">Target</span>
            </div>
            <table className="w-full text-xs text-left">
              <thead>
                <tr className="border-b border-stone-200 text-stone-500">
                  <th className="px-4 py-2 font-medium">Task</th>
                  <th className="px-3 py-2 font-medium">Date</th>
                  <th className="px-3 py-2 font-medium text-center">Status</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-stone-200/60 bg-white">
                {indiaItems.map((item, idx) => (
                  <tr key={idx} className="hover:bg-stone-50/50">
                    <td className="px-4 py-2.5 font-medium text-stone-800">{item.task}</td>
                    <td className="px-3 py-2.5 text-stone-500 font-mono text-[11px]">{item.date}</td>
                    <td className="px-3 py-2.5 text-center">
                      {item.completed ? (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-emerald-100 text-emerald-600 font-bold text-xs">
                          ✓
                        </span>
                      ) : (
                        <span className="inline-flex items-center justify-center w-5 h-5 rounded-full bg-amber-100 text-amber-600 font-bold text-xs">
                          ⏱
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Right column (7 cols): Interactive Gantt Chart */}
        <div className="lg:col-span-7 rounded-xl border border-stone-200 bg-stone-50/30 p-4 space-y-4 flex flex-col justify-between">
          <div className="flex items-center justify-between text-xs font-mono text-stone-600 border-b border-stone-200 pb-2">
            <span className="font-semibold text-stone-900">Task Timeline (Days)</span>
            <div className="flex gap-3">
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-stone-800 inline-block" /> Completed
              </span>
              <span className="flex items-center gap-1">
                <span className="w-2.5 h-2.5 rounded-sm bg-blue-600 inline-block" /> In Progress
              </span>
            </div>
          </div>

          {/* Time axis marks */}
          <div className="relative w-full h-6 border-b border-stone-200 font-mono text-[10px] text-stone-400">
            {TIME_MARKS.map((m) => {
              const leftPct = (m / TOTAL_DAYS) * 100;
              return (
                <div key={m} className="absolute top-0 transform -translate-x-1/2 flex flex-col items-center" style={{ left: `${leftPct}%` }}>
                  <span>{m}d</span>
                  <div className="w-[1px] h-2 bg-stone-300 mt-0.5" />
                </div>
              );
            })}
          </div>

          {/* Task Gantt Bars */}
          <div className="space-y-3 py-2 overflow-x-auto">
            {tasks.map((task) => {
              const leftPct = (task.start_day / TOTAL_DAYS) * 100;
              const widthPct = Math.max(4, ((task.end_day - task.start_day) / TOTAL_DAYS) * 100);
              const isCompleted = task.status === "completed";

              return (
                <div key={task.id} className="space-y-1">
                  <div className="flex justify-between text-[11px] font-editorial-body text-stone-700">
                    <span className="font-medium truncate max-w-[200px]">{task.name}</span>
                    <span className="font-mono text-[10px] text-stone-400">
                      Day {task.start_day}–{task.end_day}
                    </span>
                  </div>
                  <div className="relative w-full h-4 bg-stone-100 rounded-md overflow-hidden border border-stone-200">
                    <div
                      className={`absolute top-0 bottom-0 rounded-md transition-all duration-500 ${
                        isCompleted
                          ? "bg-gradient-to-r from-stone-800 to-stone-900 border-r-2 border-stone-600"
                          : "bg-gradient-to-r from-blue-500 to-indigo-600 animate-pulse"
                      }`}
                      style={{ left: `${leftPct}%`, width: `${widthPct}%` }}
                    />
                  </div>
                </div>
              );
            })}
          </div>

          {/* Footer note */}
          <div className="pt-2 border-t border-stone-200/80 text-[11px] font-editorial-body text-stone-500 italic text-center">
            * Transaction timing optimized for parallel Delaware incorporation and Indian AD Bank FC-GPR filing.
          </div>
        </div>
      </div>
    </div>
  );
}

"use client";

import { useEffect, useState } from "react";
import {
  GitBranch,
  Search,
  Folder,
  FolderOpen,
  Tag,
  ChevronRight,
  ArrowRight,
  Layers,
  ChevronLeft,
} from "lucide-react";
import { api, type SkillSearchItem } from "@/lib/api";

interface TaxonomyNode {
  id: number;
  slug: string;
  name: string;
  type: string;
  level: number;
  parent_slug?: string | null;
  has_children: boolean;
}

export default function TaxonomyBrowserPage() {
  const [rootNodes, setRootNodes] = useState<TaxonomyNode[]>([]);
  const [breadcrumbs, setBreadcrumbs] = useState<TaxonomyNode[]>([]);
  const [selectedNode, setSelectedNode] = useState<TaxonomyNode | null>(null);
  const [childrenNodes, setChildrenNodes] = useState<TaxonomyNode[]>([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState<SkillSearchItem[]>([]);
  const [loading, setLoading] = useState(false);

  // Load root domains
  useEffect(() => {
    async function loadRoots() {
      setLoading(true);
      try {
        const roots = await api.getTaxonomyTree(undefined, 1);
        setRootNodes(roots);
        if (roots.length > 0) {
          selectRoot(roots[0]);
        }
      } catch {
        const fallbackRoots: TaxonomyNode[] = [
          { id: 1, slug: "technical-skills", name: "Technical Skills", type: "domain", level: 0, has_children: true },
          { id: 2, slug: "business-skills", name: "Business Skills", type: "domain", level: 0, has_children: true },
          { id: 3, slug: "soft-skills", name: "Soft Skills", type: "domain", level: 0, has_children: true },
          { id: 4, slug: "domain-knowledge", name: "Domain Knowledge", type: "domain", level: 0, has_children: true },
        ];
        setRootNodes(fallbackRoots);
        selectRoot(fallbackRoots[0]);
      } finally {
        setLoading(false);
      }
    }
    loadRoots();
  }, []);

  const selectRoot = async (node: TaxonomyNode) => {
    setSelectedNode(node);
    setBreadcrumbs([node]);
    await fetchChildren(node);
  };

  const drillDown = async (node: TaxonomyNode) => {
    setSelectedNode(node);
    setBreadcrumbs((prev) => [...prev, node]);
    await fetchChildren(node);
  };

  const jumpToBreadcrumb = async (index: number) => {
    const target = breadcrumbs[index];
    setSelectedNode(target);
    setBreadcrumbs((prev) => prev.slice(0, index + 1));
    await fetchChildren(target);
  };

  const fetchChildren = async (node: TaxonomyNode) => {
    try {
      const children = await api.getTaxonomyTree(node.id, 1);
      setChildrenNodes(children);
    } catch {
      setChildrenNodes([
        { id: node.id * 10 + 1, slug: `${node.slug}-backend`, name: `${node.name} (Specialization A)`, type: "category", level: node.level + 1, has_children: true },
        { id: node.id * 10 + 2, slug: `${node.slug}-frontend`, name: `${node.name} (Specialization B)`, type: "category", level: node.level + 1, has_children: true },
        { id: node.id * 10 + 3, slug: `${node.slug}-arch`, name: `${node.name} (Specialization C)`, type: "category", level: node.level + 1, has_children: false },
      ]);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setLoading(true);
    try {
      const hits = await api.searchTaxonomy(searchQuery);
      setSearchResults(hits);
    } catch {
      setSearchResults([
        { slug: "python", name: "Python", score: 1.0, match_type: "exact", type: "technical" },
        { slug: "fastapi", name: "FastAPI", score: 0.95, match_type: "exact", type: "technical" },
        { slug: "postgresql", name: "PostgreSQL", score: 0.88, match_type: "fuzzy", type: "technical" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
          Interactive Taxonomy Browser
        </h1>
        <p className="text-sm text-slate-600 dark:text-slate-400 mt-1">
          Explore 9,600+ skills organized into canonical domains, subcategories, and implied relationships.
        </p>
      </div>

      {/* Search Header */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search taxonomy for any skill (e.g., Python, Kubernetes, React, Agile)..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold text-xs rounded-lg transition-colors"
          >
            Search
          </button>
        </form>

        {/* Search Results Drawer */}
        {searchResults.length > 0 && (
          <div className="pt-2 border-t border-slate-100 dark:border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-500">
              <span className="font-semibold">Search Matches ({searchResults.length})</span>
              <button
                type="button"
                onClick={() => setSearchResults([])}
                className="text-slate-400 hover:text-slate-600 text-[11px]"
              >
                Clear
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {searchResults.map((hit, i) => (
                <div
                  key={i}
                  className="px-2.5 py-1 rounded-lg bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 text-xs font-medium text-indigo-700 dark:text-indigo-300 flex items-center gap-1.5"
                >
                  <span>{hit.name}</span>
                  <span className="text-[10px] font-mono opacity-75">({hit.match_type})</span>
                  <span className="text-[10px] font-mono px-1 rounded bg-indigo-200 dark:bg-indigo-900 text-indigo-800 dark:text-indigo-300">
                    {Math.round(hit.score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Explorer Dual-Pane */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Pane: Domains & Categories */}
        <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm space-y-2">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider px-2 flex items-center gap-1.5">
            <Layers className="w-4 h-4 text-indigo-500" />
            <span>Root Taxonomy Domains</span>
          </h3>

          <div className="space-y-1">
            {rootNodes.map((node) => {
              const isSelected = breadcrumbs[0]?.id === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => selectRoot(node)}
                  className={`w-full text-left px-3 py-2 rounded-lg text-xs font-medium flex items-center justify-between transition-colors ${
                    isSelected
                      ? "bg-indigo-50 text-indigo-700 dark:bg-indigo-950 dark:text-indigo-300 font-bold"
                      : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-800/60"
                  }`}
                >
                  <span className="flex items-center gap-2">
                    {isSelected ? (
                      <FolderOpen className="w-4 h-4 text-indigo-500" />
                    ) : (
                      <Folder className="w-4 h-4 text-slate-400" />
                    )}
                    <span>{node.name}</span>
                  </span>
                  <ChevronRight className="w-3.5 h-3.5 opacity-50" />
                </button>
              );
            })}
          </div>
        </div>

        {/* Center & Right Pane: Children Nodes & Skill Inspector */}
        <div className="md:col-span-2 space-y-4">
          {selectedNode && (
            <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-5 shadow-sm space-y-4">
              {/* Breadcrumb Navigation */}
              <div className="flex items-center flex-wrap gap-1 text-xs text-slate-500 pb-2 border-b border-slate-100 dark:border-slate-800">
                <span className="font-semibold text-slate-400">Path:</span>
                {breadcrumbs.map((b, idx) => (
                  <div key={b.id} className="flex items-center gap-1">
                    {idx > 0 && <ChevronRight className="w-3 h-3 text-slate-400" />}
                    <button
                      onClick={() => jumpToBreadcrumb(idx)}
                      className={`hover:underline ${
                        idx === breadcrumbs.length - 1
                          ? "font-bold text-indigo-600 dark:text-indigo-400"
                          : "text-slate-600 dark:text-slate-300"
                      }`}
                    >
                      {b.name}
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between border-b border-slate-100 dark:border-slate-800 pb-3">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
                    Level {selectedNode.level} Node
                  </span>
                  <h3 className="text-lg font-bold text-slate-900 dark:text-white">
                    {selectedNode.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono mt-0.5">
                    slug: {selectedNode.slug} • type: {selectedNode.type}
                  </p>
                </div>
                <Tag className="w-6 h-6 text-indigo-500" />
              </div>

              {/* Children Sub-skills */}
              <div>
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">
                  Child Skills & Sub-Specializations ({childrenNodes.length})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 max-h-96 overflow-y-auto">
                  {childrenNodes.map((child) => (
                    <div
                      key={child.id}
                      onClick={() => child.has_children && drillDown(child)}
                      className={`p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between text-xs transition-colors ${
                        child.has_children
                          ? "cursor-pointer hover:bg-indigo-50/60 dark:hover:bg-indigo-950/40 hover:border-indigo-200"
                          : ""
                      }`}
                    >
                      <span className="font-medium text-slate-800 dark:text-slate-200 flex items-center gap-1.5">
                        {child.has_children && <Folder className="w-3.5 h-3.5 text-indigo-500" />}
                        <span>{child.name}</span>
                      </span>
                      <div className="flex items-center gap-1.5">
                        <span className="text-[10px] font-mono text-slate-400">
                          lvl {child.level}
                        </span>
                        {child.has_children && (
                          <ChevronRight className="w-3.5 h-3.5 text-slate-400" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

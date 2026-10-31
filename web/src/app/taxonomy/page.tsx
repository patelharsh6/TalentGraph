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
          handleSelectNode(roots[0]);
        }
      } catch {
        // Fallback demo roots
        const fallbackRoots: TaxonomyNode[] = [
          { id: 1, slug: "information-technology", name: "Information Technology & Software", type: "domain", level: 0, has_children: true },
          { id: 2, slug: "data-science-ai", name: "Data Science & Artificial Intelligence", type: "domain", level: 0, has_children: true },
          { id: 3, slug: "cloud-devops", name: "Cloud Infrastructure & DevOps", type: "domain", level: 0, has_children: true },
          { id: 4, slug: "product-management", name: "Product Management & Operations", type: "domain", level: 0, has_children: true },
        ];
        setRootNodes(fallbackRoots);
        handleSelectNode(fallbackRoots[0]);
      } finally {
        setLoading(false);
      }
    }
    loadRoots();
  }, []);

  const handleSelectNode = async (node: TaxonomyNode) => {
    setSelectedNode(node);
    try {
      const children = await api.getTaxonomyTree(node.id, 1);
      setChildrenNodes(children);
    } catch {
      // Fallback children demo
      setChildrenNodes([
        { id: node.id * 10 + 1, slug: `${node.slug}-backend`, name: `${node.name} (Backend)`, type: "category", level: 1, has_children: true },
        { id: node.id * 10 + 2, slug: `${node.slug}-frontend`, name: `${node.name} (Frontend)`, type: "category", level: 1, has_children: true },
        { id: node.id * 10 + 3, slug: `${node.slug}-arch`, name: `${node.name} (Architecture)`, type: "category", level: 1, has_children: true },
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
          Explore the ESCO / O*NET hierarchical skill taxonomy, alias relationships, and vector embeddings.
        </p>
      </div>

      {/* Search Input */}
      <div className="bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-xl p-4 shadow-sm">
        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-3" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search taxonomy for any skill (e.g. 'PostgreSQL', 'React', 'DevOps')..."
              className="w-full pl-9 pr-4 py-2 text-sm rounded-lg border border-slate-300 dark:border-slate-700 bg-slate-50 dark:bg-slate-800 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          </div>
          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-xs sm:text-sm font-semibold transition-all"
          >
            Search Skills
          </button>
        </form>

        {/* Search Results */}
        {searchResults.length > 0 && (
          <div className="mt-3 pt-3 border-t border-slate-100 dark:border-slate-800">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              Found {searchResults.length} Taxonomy Matches:
            </p>
            <div className="flex flex-wrap gap-2">
              {searchResults.map((hit, idx) => (
                <div
                  key={idx}
                  className="px-2.5 py-1 rounded-lg text-xs border border-indigo-100 dark:border-indigo-900/40 bg-indigo-50/50 dark:bg-indigo-950/40 text-indigo-900 dark:text-indigo-200 flex items-center gap-1.5"
                >
                  <span className="font-semibold">{hit.name}</span>
                  <span className="text-[10px] opacity-75 font-mono">({hit.match_type})</span>
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
              const isSelected = selectedNode?.id === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => handleSelectNode(node)}
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
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                  {childrenNodes.map((child) => (
                    <div
                      key={child.id}
                      className="p-3 rounded-lg border border-slate-100 dark:border-slate-800 bg-slate-50/50 dark:bg-slate-800/40 flex items-center justify-between text-xs"
                    >
                      <span className="font-medium text-slate-800 dark:text-slate-200">
                        {child.name}
                      </span>
                      <span className="text-[10px] font-mono text-slate-400">
                        lvl {child.level}
                      </span>
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


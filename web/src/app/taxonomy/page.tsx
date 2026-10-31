"use client";

import { useEffect, useState } from "react";
import { motion } from "framer-motion";
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
  Sparkles,
  X,
} from "lucide-react";
import { Card } from "@/components/ui/Card";
import { Button } from "@/components/ui/Button";
import { Badge } from "@/components/ui/Badge";
import { SectionHeader } from "@/components/ui/SectionHeader";
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
        { slug: "scikit-learn", name: "Scikit-Learn", score: 0.88, match_type: "fuzzy", type: "technical" },
        { slug: "fastapi", name: "FastAPI", score: 0.82, match_type: "embedding", type: "technical" },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25 }}
      className="space-y-8"
    >
      {/* Page Header */}
      <SectionHeader
        eyebrow="Taxonomy Graph DAG"
        eyebrowIcon={<GitBranch className="w-3.5 h-3.5" />}
        title="ESCO & O*NET Taxonomy Explorer"
        gradientWord="Taxonomy Explorer"
        subtitle="Hierarchical directed acyclic graph of 3,000+ standardized skills, parent concepts, and semantic aliases."
      />

      {/* Search Header Card */}
      <Card className="p-6 space-y-4">
        <form onSubmit={handleSearch} className="flex gap-2.5">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3.5 pointer-events-none" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search taxonomy for any skill (e.g., Python, Kubernetes, React, Agile)..."
              className="w-full pl-10 pr-4 py-2.5 text-sm rounded-xl border border-slate-200 dark:border-white/10 bg-slate-50/70 dark:bg-white/5 text-slate-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-brand-500 font-medium"
            />
          </div>
          <Button type="submit" size="md" variant="primary">
            Search
          </Button>
        </form>

        {/* Search Results Drawer */}
        {searchResults.length > 0 && (
          <div className="pt-3 border-t border-slate-100 dark:border-white/10 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
              <span className="font-bold uppercase tracking-wider text-[11px]">
                Search Matches ({searchResults.length})
              </span>
              <button
                type="button"
                onClick={() => setSearchResults([])}
                className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 text-xs font-semibold flex items-center gap-1"
              >
                <X className="w-3 h-3" />
                <span>Clear</span>
              </button>
            </div>
            <div className="flex flex-wrap gap-2">
              {searchResults.map((hit, i) => (
                <div
                  key={i}
                  className="px-3 py-1.5 rounded-full bg-brand-50 dark:bg-brand-950/60 border border-brand-200/80 dark:border-brand-800/60 text-xs font-medium text-brand-700 dark:text-brand-300 flex items-center gap-2 shadow-sm"
                >
                  <span className="font-semibold">{hit.name}</span>
                  <span className="text-[10px] font-mono opacity-70">({hit.match_type})</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded-full bg-brand-200/80 dark:bg-brand-900 text-brand-900 dark:text-brand-200 font-bold">
                    {Math.round(hit.score * 100)}%
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Explorer Dual-Pane */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Left Pane: Domains & Categories */}
        <Card className="p-5 space-y-3">
          <h3 className="text-xs font-bold text-slate-500 uppercase tracking-wider px-2 flex items-center gap-2">
            <Layers className="w-4 h-4 text-brand-500" />
            <span>Root Taxonomy Domains</span>
          </h3>

          <div className="space-y-1">
            {rootNodes.map((node) => {
              const isSelected = breadcrumbs[0]?.id === node.id;
              return (
                <button
                  key={node.id}
                  onClick={() => selectRoot(node)}
                  className={`w-full text-left px-3.5 py-2.5 rounded-xl text-xs font-semibold flex items-center justify-between transition-all duration-150 ${
                    isSelected
                      ? "bg-brand-50 text-brand-700 dark:bg-brand-950/70 dark:text-brand-300 border border-brand-200/80 dark:border-brand-800 shadow-sm"
                      : "text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-white/5 border border-transparent"
                  }`}
                >
                  <span className="flex items-center gap-2.5">
                    {isSelected ? (
                      <FolderOpen className="w-4 h-4 text-brand-600 dark:text-brand-400" />
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
        </Card>

        {/* Center & Right Pane: Children Nodes & Skill Inspector */}
        <div className="md:col-span-2 space-y-4">
          {selectedNode && (
            <Card className="p-6 space-y-5">
              {/* Breadcrumb Navigation */}
              <div className="flex items-center flex-wrap gap-1.5 text-xs text-slate-500 pb-3 border-b border-slate-100 dark:border-white/10">
                <span className="font-bold text-slate-400 text-[11px] uppercase tracking-wider">Path:</span>
                {breadcrumbs.map((b, idx) => (
                  <div key={b.id} className="flex items-center gap-1.5">
                    {idx > 0 && <ChevronRight className="w-3 h-3 text-slate-400" />}
                    <button
                      onClick={() => jumpToBreadcrumb(idx)}
                      className={`hover:underline transition-colors ${
                        idx === breadcrumbs.length - 1
                          ? "font-bold text-brand-600 dark:text-brand-400"
                          : "text-slate-600 dark:text-slate-300 font-medium"
                      }`}
                    >
                      {b.name}
                    </button>
                  </div>
                ))}
              </div>

              <div className="flex items-center justify-between border-b border-slate-100 dark:border-white/10 pb-4">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400 font-bold">
                    Level {selectedNode.level} Node
                  </span>
                  <h3 className="text-xl font-extrabold text-slate-900 dark:text-white">
                    {selectedNode.name}
                  </h3>
                  <p className="text-xs text-slate-500 font-mono mt-1">
                    slug: {selectedNode.slug} • type: {selectedNode.type}
                  </p>
                </div>
                <div className="w-10 h-10 rounded-2xl bg-brand-50 dark:bg-brand-950/60 border border-brand-200 dark:border-brand-800 flex items-center justify-center text-brand-600 dark:text-brand-400 shadow-sm">
                  <Tag className="w-5 h-5" />
                </div>
              </div>

              {/* Children Sub-skills */}
              <div className="space-y-3">
                <h4 className="text-xs font-bold text-slate-500 uppercase tracking-wider">
                  Child Skills & Sub-Specializations ({childrenNodes.length})
                </h4>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 max-h-96 overflow-y-auto pr-1">
                  {childrenNodes.map((child) => (
                    <div
                      key={child.id}
                      onClick={() => child.has_children && drillDown(child)}
                      className={`p-3.5 rounded-xl border border-slate-100 dark:border-white/10 bg-slate-50/60 dark:bg-white/5 flex items-center justify-between text-xs transition-all duration-150 ${
                        child.has_children
                          ? "cursor-pointer hover:bg-brand-50/70 dark:hover:bg-brand-950/40 hover:border-brand-200 hover:-translate-y-0.5 shadow-sm"
                          : ""
                      }`}
                    >
                      <span className="font-semibold text-slate-800 dark:text-slate-200 flex items-center gap-2">
                        {child.has_children && <Folder className="w-3.5 h-3.5 text-brand-500" />}
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
            </Card>
          )}
        </div>
      </div>
    </motion.div>
  );
}

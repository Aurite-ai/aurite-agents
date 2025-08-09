import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Home, Users, Workflow, Database, Cloud } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Logo } from '@/components/Logo';
import { ConnectionStatus } from '@/components/ConnectionStatus';

const sidebarItems = [
  { icon: Home, label: 'Home', id: 'home', path: '/' },
  { icon: Users, label: 'All Agents', id: 'agents', path: '/agents' },
  { icon: Workflow, label: 'Workflows', id: 'workflows', path: '/workflows' },
];

const configItems = [
  { icon: Database, label: 'MCP Clients', id: 'mcp', path: '/mcp-clients' },
  { icon: Cloud, label: 'LLM Configs', id: 'llm', path: '/llm-configs' },
];

export default function Sidebar() {
  const [sidebarHovered, setSidebarHovered] = useState(false);
  const location = useLocation();

  // Determine active tab based on current path
  const getActiveTab = () => {
    const path = location.pathname;
    if (path === '/') {
      return 'home';
    }
    if (path.startsWith('/agents')) {
      return 'agents';
    }
    if (path.startsWith('/workflows')) {
      return 'workflows';
    }
    if (path.startsWith('/mcp-clients')) {
      return 'mcp';
    }
    if (path.startsWith('/llm-configs')) {
      return 'llm';
    }
    return '';
  };

  const activeTab = getActiveTab();

  return (
    <motion.div
      initial={{ x: -80 }}
      animate={{
        x: 0,
        width: sidebarHovered ? 250 : 80,
      }}
      transition={{ duration: 0.3 }}
      onMouseEnter={() => setSidebarHovered(true)}
      onMouseLeave={() => setSidebarHovered(false)}
      className={`${sidebarHovered ? 'w-64' : 'w-20'} gradient-sidebar border-r border-border flex flex-col py-6 h-full`}
    >
      {/* Logo */}
      <div className={`mb-12 ${sidebarHovered ? 'px-6' : 'flex justify-center'}`}>
        {sidebarHovered ? (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.2 }}
            className="flex items-center gap-3"
          >
            <Logo className="w-10 h-10" />
            <h1 className="text-xl font-bold text-foreground">Agent Studio</h1>
          </motion.div>
        ) : (
          <Logo className="w-10 h-10" />
        )}
      </div>

      {/* Navigation */}
      <nav className={`flex flex-col space-y-3 ${sidebarHovered ? 'px-4' : 'items-center'}`}>
        {sidebarItems.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: index * 0.1 }}
            className="group relative"
          >
            <Link to={item.path} className="block">
              <Button
                variant={activeTab === item.id ? 'default' : 'ghost'}
                className={`${sidebarHovered ? 'w-full justify-start gap-3 h-11' : 'w-12 h-12'} rounded-xl`}
              >
                <item.icon className="h-5 w-5" />
                {sidebarHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    {item.label}
                  </motion.span>
                )}
              </Button>
            </Link>
            {/* Tooltip for collapsed state */}
            {!sidebarHovered && (
              <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-popover text-popover-foreground px-2 py-1 rounded-md text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </div>
            )}
          </motion.div>
        ))}

        <div
          className={`${sidebarHovered ? 'w-full h-px' : 'w-8 h-px'} bg-border my-6 ${!sidebarHovered && 'mx-auto'}`}
        />

        {sidebarHovered && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-4 px-3"
          >
            AI Component Configuration
          </motion.div>
        )}

        {configItems.map((item, index) => (
          <motion.div
            key={item.label}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: (sidebarItems.length + index) * 0.1 }}
            className="group relative"
          >
            <Link to={item.path} className="block">
              <Button
                variant={activeTab === item.id ? 'default' : 'ghost'}
                className={`${sidebarHovered ? 'w-full justify-start gap-3 h-11' : 'w-12 h-12'} rounded-xl`}
              >
                <item.icon className="h-5 w-5" />
                {sidebarHovered && (
                  <motion.span
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 }}
                  >
                    {item.label}
                  </motion.span>
                )}
              </Button>
            </Link>
            {/* Tooltip for collapsed state */}
            {!sidebarHovered && (
              <div className="absolute left-16 top-1/2 -translate-y-1/2 bg-popover text-popover-foreground px-2 py-1 rounded-md text-sm opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-50">
                {item.label}
              </div>
            )}
          </motion.div>
        ))}
      </nav>

      {/* Connection Status - Fixed at bottom */}
      <div className={`mt-auto ${sidebarHovered ? 'px-4' : 'flex justify-center'} pb-2`}>
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.8 }}
          className="w-full justify-center flex"
        >
          <ConnectionStatus isExpanded={sidebarHovered} />
        </motion.div>
      </div>
    </motion.div>
  );
}

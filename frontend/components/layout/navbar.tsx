"use client";

import { Button } from "@/components/ui/button";

export function Navbar() {
  const handleLoginClick = () => {
    // TODO: Implement login functionality
    console.log("Login clicked");
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo/Brand */}
        <div className="flex items-center">
          <span className="text-2xl font-bold text-primary">EventPilot</span>
        </div>

        {/* Login Button */}
        <div className="flex items-center gap-4">
          <Button onClick={handleLoginClick} size="default">
            Login
          </Button>
        </div>
      </div>
    </nav>
  );
}

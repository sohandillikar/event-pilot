"use client";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/hooks/use-auth";
import { signInWithGoogle, signOut } from "@/lib/actions/auth";
import { useTransition } from "react";

export function Navbar() {
  const { user, loading } = useAuth();
  const [isPending, startTransition] = useTransition();

  const handleLoginClick = () => {
    startTransition(async () => {
      await signInWithGoogle();
    });
  };

  const handleLogoutClick = () => {
    startTransition(async () => {
      await signOut();
    });
  };

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto flex h-16 items-center justify-between px-4 sm:px-6 lg:px-8">
        {/* Logo/Brand */}
        <div className="flex items-center">
          <span className="text-2xl font-bold text-primary">EventPilot</span>
        </div>

        {/* Auth Button */}
        <div className="flex items-center gap-4">
          {loading ? (
            <div className="h-9 w-20 animate-pulse rounded-md bg-muted" />
          ) : user ? (
            <Button 
              onClick={handleLogoutClick} 
              size="default"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Spinner className="mr-2" />
                  Logging out...
                </>
              ) : "Logout"}
            </Button>
          ) : (
            <Button 
              onClick={handleLoginClick} 
              size="default"
              disabled={isPending}
            >
              {isPending ? (
                <>
                  <Spinner className="mr-2" />
                  Logging in...
                </>
              ) : "Login"}
            </Button>
          )}
        </div>
      </div>
    </nav>
  );
}

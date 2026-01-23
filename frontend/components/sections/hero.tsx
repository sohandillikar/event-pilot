"use client";

import { Button } from "@/components/ui/button";
import { Spinner } from "@/components/ui/spinner";
import { useAuth } from "@/hooks/use-auth";
import { signInWithGoogle } from "@/lib/actions/auth";
import { useRouter } from "next/navigation";
import { useTransition } from "react";

export function Hero() {
  const { user } = useAuth();
  const router = useRouter();
  const [isPending, startTransition] = useTransition();

  const handleGetStarted = () => {
    if (user) {
      // User is already logged in, redirect to dashboard
      router.push("/dashboard");
    } else {
      // User not logged in, trigger Google sign in
      startTransition(async () => {
        await signInWithGoogle();
      });
    }
  };

  return (
    <section className="relative flex min-h-screen items-center justify-center px-4 sm:px-6 lg:px-8">
      {/* Subtle gradient background */}
      <div className="absolute inset-0 -z-10 bg-gradient-to-b from-primary/5 via-background to-background" />

      <div className="container mx-auto max-w-5xl py-20 text-center">
        {/* Main Headline */}
        <h1 className="mb-6 text-5xl font-bold tracking-tight text-foreground sm:text-6xl lg:text-7xl">
          Plan Corporate Events in{" "}
          <span className="text-primary">Minutes,</span> Not Weeks
        </h1>

        {/* Subheadline */}
        <p className="mx-auto mb-10 max-w-2xl text-lg text-muted-foreground sm:text-xl lg:text-2xl">
          From venue sourcing to negotiation, find the best venues at the best
          prices with our multi-agent AI system
        </p>

        {/* CTA Button */}
        <div className="flex flex-col items-center justify-center gap-4 sm:flex-row">
          <Button
            onClick={handleGetStarted}
            size="lg"
            className="text-base"
            disabled={isPending}
          >
            {isPending ? (
              <>
                <Spinner className="mr-2" />
                Loading...
              </>
            ) : "Get Started"}
          </Button>
        </div>

        {/* Optional: Add some trust indicators or key benefits */}
        <div className="mt-16 grid grid-cols-1 gap-8 sm:grid-cols-3">
          <div className="flex flex-col items-center gap-2">
            <div className="text-4xl font-bold text-primary">10x</div>
            <p className="text-sm text-muted-foreground">Faster Planning</p>
          </div>
          <div className="flex flex-col items-center gap-2">
            <div className="text-4xl font-bold text-primary">50%</div>
            <p className="text-sm text-muted-foreground">Cost Savings</p>
          </div>
          <div className="flex flex-col items-center gap-2">
            <div className="text-4xl font-bold text-primary">24/7</div>
            <p className="text-sm text-muted-foreground">AI Assistance</p>
          </div>
        </div>
      </div>
    </section>
  );
}

import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { createUserWithEmailAndPassword, updateProfile } from "firebase/auth";
import { auth } from "../firebase"; // import firebase auth instance

const Signup = () => {
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const navigate = useNavigate();

  const handleSignup = async (e) => {
    e.preventDefault();
    setError("");

    try {
      // Create a new user with Firebase Auth
      const userCredential = await createUserWithEmailAndPassword(
        auth,
        email,
        password
      );

      // Optional: update display name
      await updateProfile(userCredential.user, { displayName: name });

      alert("Signup successful! Please log in.");
      navigate("/"); // Redirect to login page after signup
    } catch (err) {
      if (err.code === "auth/email-already-in-use") {
        setError("This email is already registered.");
      } else if (err.code === "auth/invalid-email") {
        setError("Please enter a valid email address.");
      } else if (err.code === "auth/weak-password") {
        setError("Password should be at least 6 characters.");
      } else {
        setError("Something went wrong. Please try again later.");
      }
    }
  };

  return (
    <div className="bg-white p-6 rounded-lg shadow-md w-96 mx-auto mt-10">
      <h2 className="text-2xl font-bold mb-4 text-center">Sign Up</h2>
      <form onSubmit={handleSignup}>
        <input
          type="text"
          placeholder="Full Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          className="border border-gray-300 rounded w-full p-2 mb-3"
          required
        />
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="border border-gray-300 rounded w-full p-2 mb-3"
          required
        />
        <input
          type="password"
          placeholder="Password (min 6 characters)"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="border border-gray-300 rounded w-full p-2 mb-3"
          required
        />
        <button
          type="submit"
          className="bg-green-500 text-white w-full py-2 rounded hover:bg-green-600"
        >
          Sign Up
        </button>
      </form>

      {/* Error message */}
      {error && <p className="text-red-500 text-center mt-3">{error}</p>}

      <p className="text-center text-sm mt-4">
        Already have an account?{" "}
        <Link to="/" className="text-blue-500 hover:underline">
          Log in
        </Link>
      </p>
    </div>
  );
};

export default Signup;
